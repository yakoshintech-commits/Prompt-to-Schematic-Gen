# KG Expansion Charter

## Goal
Grow the curated component knowledge graph from 243 parts toward meaningful
coverage of the 20,308-entry candidate pool (`PCBSchemaGen_v2/kg/kg_candidate_pool.json`),
at the same curation rigor already proven on `Antenna`/`Stepper_Motor_bipolar`
and this session's batches — not a bulk, unverified merge. This is standing,
ongoing work, not a side task: production-grade vague-prompt-to-schematic
coverage is the actual deliverable.

## Why batches, not a bulk merge (evidence, not caution for its own sake)
Four separate times this project has measured that changing the candidate
pool a generation model chooses from — even with individually-correct
additions — can regress accuracy on the existing, already-working set
(T027, T032, T033, and the reverted SchGen diversity-fix detour). Pool size
and composition are themselves a measured risk factor, independent of data
quality. So: small batches, hand-verified, each followed by a full
regression check before the next batch starts.

## Per-batch process
1. Pull candidates from `kg_candidate_pool.json`, prioritized for real-world
   usefulness and genuine gaps in current coverage (check the live KG first —
   don't duplicate what's already curated).
2. Prefer clean, unambiguously-named real pins. Deliberately defer
   all-unnamed-pin (`~`) parts until there's headroom to test them
   specifically — that's the exact failure class (pin-naming hallucination)
   this session already spent real effort fixing; don't reintroduce more of
   it while that fix is still being validated.
3. Hand-assign `pin_roles` only where unambiguous, matching established
   convention exactly (`i2c_sda`/`i2c_scl`, `supply_vdd`/`supply_gnd`,
   `usb_vbus`/`usb_dp`/`usb_dm`/`usb_shield`, `logic_in`/`logic_out`, etc. —
   check `phase2_checks.py`'s `_GENERIC_ROLE_FAMILIES` before inventing a new
   family, so new roles actually participate in existing checks instead of
   silently falling outside them).
4. Stage drafts (not live KG) until a batch is complete, then merge.
5. Live-test each new part in isolation via real Layer 1 generation before
   trusting it structurally resolves.
6. Run a full-population regression validation after merging a batch,
   before starting the next one. Compare the clean, matched diff — not the
   raw pass/fail count — the same discipline that caught every real
   regression this session (reused/stale baselines corrupt comparisons;
   isolated rechecks distinguish real defects from this pipeline's own
   measured nondeterminism).

## Resourcing rule
- CPU-only work (candidate selection, hand curation, drafting) has no
  resource conflict with anything GPU-bound — runs continuously, in
  parallel, regardless of what else is running.
- GPU-bound work (live-testing a new part via Layer 1/Ollama, any full
  validation run via SchGen's local model) is sequenced, never run
  concurrently with another GPU-bound job on this machine. Check
  `nvidia-smi` headroom before starting one.
- Never touch the live KG (`kg_open_schematics.json`) or pipeline config
  files while a validation run that depends on them is in progress.

## Batch log
| Batch | Parts | Status | Notes |
|---|---|---|---|
| 1 | `USB_A`, `USB_B`, `Conn_01x02`, `Conn_01x03`, `Conn_01x04`, `Transformer_1P_1S`, `Transformer_1P_2S`, `SW_DPST` | drafted, staged (not merged) | Connectors/passives, clean named pins, confirmed non-redundant vs. live KG |
| 2 | `BME280`, `SHT31-DIS`, `LM35-D`, `PCF8574`, `DS1307+`, `PCA9685PW` | drafted, staged (not merged) | Common ICs (env. sensors, I2C expander, RTC, PWM driver), `i2c_sda`/`i2c_scl` roles confirmed against existing convention |
| 3 | `L298N`, `DRV8833PW`, `ULN2003A`, `74HC595`, `74HC165` | drafted, staged (not merged) | Motor drivers + first `transistor_array`/`shift_register` subcategory entries (both genuinely new to the live KG) |
| 4 | `MAX232I`, `SP3485EN`, `MCP2515-xSO`, `ENC28J60x-SO`, `nRF24L01P` | drafted, staged (not merged) | Communication interfaces (RS232/RS485/CAN controller/2nd Ethernet chip/RF transceiver) - pulled the FULL existing `pin_roles` vocabulary from the live KG first (30 distinct roles, incl. `spi_*`, `rs485_*`, `can_*`, `eth_*`, `xtal_*`) rather than approximating; exact matches used throughout |
| 5 | `MPU-6050`, `ACS712xLCTR-20A`, `MCP4725xxx-xCH`, `MCP3008`, `TCA9548AMRGER`, `MCP23017_SO` | drafted, staged (not merged) | Motion sensor, Hall-effect current sensor, DAC, SPI ADC, I2C multiplexer, 16-bit I2C I/O expander - all genuinely new subcategories or complementary to existing (non-redundant) parts |
| 6 | `LM2596S-5`, `XL4015`, `LM7805_TO220`, `TDA2030`, `WS2811`, `Crystal` | drafted, staged (not merged) | Buck/linear regulators, audio amp, LED driver, bare 2-pin crystal - `buck_*`/`supply_vdd`/`supply_gnd`/`out`/`xtal_in`/`xtal_out` roles matched exactly against existing LDO/buck entries (`AMS1117-3.3`, `TPS54302`, etc.) |
| 7 | `Arduino_UNO_R3`, `INA219AxD`, `24LC256`, `LM393`, `TL431DBV`, `6N137`, `TXS0108EPW` | drafted, staged (not merged) | Devboard (only 11 existed), I2C power monitor, I2C EEPROM, dual comparator, shunt voltage reference, optocoupler, 8-bit level translator. `LM393`'s 2 output pins are genuinely unnamed (`~`) in the real symbol - kept as-is per the all-unnamed-pin precedent (use the number), not treated as a full defer since 6/8 pins are clearly named |
| 8 | `Fuse`, `Varistor`, `D_TVS`, `R_Potentiometer`, `Thermistor_NTC`, `LDR03`, `Micro_SD_Card` | drafted, staged (not merged) | Protection/passive parts + a genuinely new connector (Micro SD socket, only 11 connectors existed total). **Methodology refinement**: 4 of these (`Fuse`/`Varistor`/`Thermistor_NTC`/`LDR03`) are simple symmetric 2-pin passives with all-unnamed real pins - included despite the charter's all-unnamed-pin deferral rule, because that rule's actual risk (a real distinguishing NAME existing and getting mis-guessed) doesn't apply to a 2-terminal symmetric device with no real name to get wrong; relays (checked separately, all candidates fully unnamed with 4-8 *distinguishing* pins) were correctly still skipped this round for exactly that reason |
| 9 | `TL072`, `OPA188xxDBV`, `DB25_Receptacle`, `AT45DB161D-SU`, `ATECC608A-SSHDA`, `MC34063AD` | drafted, staged (not merged) | Dual/single JFET-input op-amps (`op_amp` subcategory precedent reused exactly from existing `LM358`), a genuinely new D-SUB connector (25-pin), SPI serial dataflash, I2C crypto co-processor, step-up/down/inverting switching regulator |
| 10 | `IRLZ44N`, `BSS84`, `ADS1015IDGS`, `BQ24074RGT` | drafted, staged (not merged) | N/P-channel power MOSFETs (logic-level and small-signal), I2C 12-bit 4-channel ADC, USB Li-Ion battery charger with power-path management |
| 11 | `BC337`, `2N3904`, `BAV99`, `MBR0520LT`, `LM317L_TO92`, `AMS1117-1.8`, `DS18S20` | drafted, staged (not merged) | NPN BJTs, dual switching diode, Schottky diode, adjustable + fixed LDOs, 1-Wire temp sensor. Checked `NE555P` first and correctly skipped it - redundant with already-curated `NE555D` (same part, different package only). `74HC00` also checked and skipped - mostly unnamed pins with no natural fallback, defer rule applies |
| 12 | `AM2302`, `PAM8403D`, `ADXL343`, `HX711`, `MAX98357A` | drafted, staged (not merged) | DHT22 temp/humidity module, Class-D stereo audio amp, I2C/SPI accelerometer, 24-bit load-cell ADC, I2S Class-D audio DAC/amp |
| 13 | `DS3231MZ`, `BZX84Cxx`, `TIP120`, `IRF9540N`, `MCP6001U`, `LM324`, `LP2950-3.3_TO92`, `TSL25911FN`, `INA3221` | drafted, staged (not merged) | Accurate RTC alternative, Zener diode, Darlington power BJT, P-channel power MOSFET, single + quad op-amps (reused exact `LM358` op-amp pin_role pattern), micropower LDO, I2C light sensor, triple-channel I2C power monitor. Checked and skipped `CAT24C256` (redundant with already-drafted `24LC256`), `BAT54C`/`BAT54A` (all-unnamed 3-pin dual-diode - real distinguishing roles exist, defer rule applies), `LM555xN` (redundant with already-curated `NE555D`) |
| 14 | `FT232RL`, `TSOP341xx`, `LED_RGBA`, `VL53L0CXV0DH1` | drafted, staged (not merged) | USB-UART bridge (2nd option alongside CP2102-family already in the pool, genuinely common/distinct part), IR receiver module, RGB LED, I2C time-of-flight distance sensor |
| 15 | `ATtiny102-SS`, `1N4001`, `2N7000`, `Si7021-A20`, `RotaryEncoder`, `LM386`, `HallGenerator` | drafted, staged (not merged) | Small AVR MCU, rectifier diode, logic-level small-signal MOSFET, I2C humidity/temp sensor, quadrature rotary encoder, audio power amp, Hall effect generator element. Checked and skipped `W25Q32JVZP` (redundant package variant of already-curated `W25Q32JVSS`) and `Adafruit_HUZZAH_ESP8266_breakout` (deferred - new risk class found: several real pin *names* are bare numeric strings like `"2"`/`"4"`/`"15"`, which could be confused with pin *numbers* by the generation model; not covered by the existing all-unnamed-pin rule, flagging as a new deferral reason) |
| 16 | `SX1278`, `MCP4921-ESN`, `TMP36xS`, `ACS758xCB-050B-PFF`, `LM311`, `TPS61040DBV`, `AD620` | drafted, staged (not merged) | Bare LoRa transceiver chip (complementary to existing `RFM95W-868S2` module), SPI DAC, analog temp sensor, Hall current sensor, comparator, boost regulator, instrumentation amp. `TPS61040DBV` deliberately reuses the existing `buck_*` role family for a boost topology (same functional roles apply) rather than inventing a `boost_*` family - noted explicitly, not assumed silently |
| 17 | `TMP117xxDRV`, `CCS811`, `Si7210-B-xx-IV`, `WS2812`, `TLC5940PWP`, `PCA9555D`, `DAC80502`, `Pololu_Breakout_DRV8825` | drafted, staged (not merged) | High-accuracy temp sensor, gas sensor, I2C Hall sensor, addressable RGB LED (complementary to existing WS2811 driver IC - different physical part type), 16-ch LED driver, 2nd I2C GPIO expander option (complements `MCP23017_SO`), dual-channel 16-bit DAC (complements `MCP4725xxx-xCH`), 2nd stepper driver breakout (`DRV8825` - higher current/microstepping than existing `Pololu_Breakout_A4988`, exact same `pin_roles`/`generic_constraints` pattern reused from that entry). Checked and skipped `74LS14` (all-unnamed pins, defer rule) and `74LS595` (redundant with already-drafted `74HC595`, same function different family) |
| 18+ | TBD | pending | Continue in background while GPU is busy with validation |

## Open items
- Merge batches 1-2 into the live KG once the current full-pipeline
  validation (pin-number-preference fix) completes and the GPU is free.
- Live-test each of the 20 drafted parts individually before merging.
- Run a full regression validation after the merge.
- Continue drafting further batches in parallel (CPU-only), prioritizing:
  genuine gaps in current coverage, parts that could close one of Layer 1's
  6 still-open companion-omission failures (the highest-leverage kind of
  addition - closes a known gap, not just adds breadth), then common
  real-world parts by category.
- **Checked Layer 1's known gaps explicitly (batch 6 pass), found neither is
  fixable by adding more KG data**: `IR2110`'s bootstrap-capacitor gap is a
  retrieval-ranking issue, not missing data - a generic `C` capacitor
  already exists in the live KG (confirmed via direct lookup), it simply
  doesn't surface in `IR2110`'s retrieved top-15 (already documented, T048).
  `MAX31865xAP` would need a real MCU/SPI-host in context - found clean
  candidates (`ATmega3208-X`, `ATmega4808-X`) but did NOT add either: its
  prompt text has no MCU-related keywords, so retrieval wouldn't surface
  it regardless of KG content, and T038 already proved "visible in context"
  doesn't mean "selected" for this exact failure class. Adding either would
  be padding, not a fix - noted here so a future pass doesn't re-attempt
  the same already-ruled-out idea.
