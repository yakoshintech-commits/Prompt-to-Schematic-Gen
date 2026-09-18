import json
import time
from types import MethodType

import torch
from safetensors import safe_open
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.integrations.mxfp4 import convert_moe_packed_tensors
from transformers.models.gpt_oss.modeling_gpt_oss import GptOssExperts, GptOssMLP
from peft import PeftModel

base_path = "/scratch/k2983/models/gpt-oss-20b"
adapter_path = "/scratch/k2983/models/SchGen-adapter"

# The adapter's LoRA target_parameters live only on experts at layers 7/15/23
# (see adapter_config.json). Full-model dequantize (~20B params -> bf16) doesn't
# fit in 32GB VRAM, and CPU-offloading the rest hits an accelerate/custom-MoE-forward
# device-mismatch bug. Loading normally also doesn't work: with triton_kernels
# available, transformers swizzles blocks/scales into an opaque kernel-optimized
# layout, so the raw per-parameter blocks/scales attrs the library's own dequantize()
# relies on no longer exist on the loaded module. So: keep the model MXFP4-quantized
# in memory (fits in ~14GB) and, for only the 3 targeted expert modules, read the raw
# blocks/scales straight from the safetensors shards on disk, dequantize those, and
# inject them as plain gate_up_proj/down_proj parameters.
TARGET_LAYERS = [7, 15, 23]

print("torch:", torch.__version__, "cuda:", torch.cuda.is_available(), torch.cuda.get_device_name(0))

t0 = time.time()
tok = AutoTokenizer.from_pretrained(base_path)
print("tokenizer loaded", time.time() - t0)

t0 = time.time()
model = AutoModelForCausalLM.from_pretrained(
    base_path,
    torch_dtype="auto",
    device_map="cuda",
)
print("base model loaded (mxfp4)", time.time() - t0, "mem GB:", torch.cuda.memory_allocated() / 1e9)

index = json.load(open(f"{base_path}/model.safetensors.index.json"))
weight_map = index["weight_map"]
shard_cache = {}

def load_raw(key):
    shard = weight_map[key]
    if shard not in shard_cache:
        shard_cache[shard] = safe_open(f"{base_path}/{shard}", framework="pt", device="cpu")
    return shard_cache[shard].get_tensor(key)

t0 = time.time()
for i in TARGET_LAYERS:
    mlp = model.model.layers[i].mlp
    experts = mlp.experts
    for proj in ["gate_up_proj", "down_proj"]:
        blocks = load_raw(f"model.layers.{i}.mlp.experts.{proj}_blocks")
        scales = load_raw(f"model.layers.{i}.mlp.experts.{proj}_scales")
        dequantized = convert_moe_packed_tensors(blocks, scales)
        dequantized = dequantized.transpose(1, 2).contiguous().to("cuda")
        setattr(experts, proj, torch.nn.Parameter(dequantized))
    # These 3 layers no longer have swizzled blocks/scales, so also undo the
    # instance-level forward() monkeypatches replace_with_mxfp4_linear() applied
    # (GptOssMLP.forward -> mlp_forward, Mxfp4GptOssExperts's own swizzled forward)
    # and rebind the standard plain-tensor forward methods for just these instances.
    mlp.forward = MethodType(GptOssMLP.forward, mlp)
    experts.forward = MethodType(GptOssExperts.forward, experts)
print(f"dequantized experts at layers {TARGET_LAYERS}", time.time() - t0, "mem GB:", torch.cuda.memory_allocated() / 1e9)

t0 = time.time()
model = PeftModel.from_pretrained(model, adapter_path)
print("adapter applied", time.time() - t0, "mem GB:", torch.cuda.memory_allocated() / 1e9)

# Confirm the adapter's target_parameters actually matched this time.
matched = [n for n, _ in model.named_parameters() if "lora" in n.lower() and "experts" in n]
print(f"expert LoRA params matched: {len(matched)}")
for n in matched[:6]:
    print(" -", n)

prompt = "I would like a 3.3V voltage regulator based on AP2112K"
messages = [{"role": "user", "content": prompt}]
inputs = tok.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt").to("cuda")

t0 = time.time()
with torch.no_grad():
    out = model.generate(inputs, max_new_tokens=200, do_sample=False)
print("generation done", time.time() - t0)
print(tok.decode(out[0][inputs.shape[-1]:], skip_special_tokens=True))
