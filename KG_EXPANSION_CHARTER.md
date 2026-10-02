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
| 18 | `Speaker`, `APDS-9960`, `TMP102xxDRL`, `MCP4728`, `74HC4051`, `ULN2803A` | drafted, staged (not merged) | Generic speaker, I2C gesture/proximity sensor, small I2C temp sensor, quad-channel I2C DAC (complements single-channel `MCP4725xxx-xCH`), 8-channel analog mux/demux, 8-channel Darlington array (complements existing 7-channel `ULN2003A` - genuinely distinct real part, higher channel count). Checked `PC817`/`H11L1` optocouplers - both all-unnamed pins with real distinguishing roles, correctly deferred per the established exception rule (same reasoning as relays) |
| 19 | `MCP4822`, `IRLML0030`, `TPS2051CDBV`, `W25X40CLSN` | drafted, staged (not merged) | 2-channel SPI DAC, small logic-level power MOSFET (SOT-23), load/power switch IC (genuinely new subcategory), 2nd SPI flash option (complements `AT45DB161D-SU`). Smaller batch - deliberately skipped `BNO055` (ambiguous pin layout: generic `PIN1`/`PIN7`-style names and unclear bus-select pins, would require guessing) and `INA169` (1 of 5 pins genuinely unnamed with unclear function) rather than curate with uncertain data |
| 20 | `L293`, `IR2104`, `LM7812_TO220`, `LM7912_TO220`, `BAT85`, `D_TVS_Filled` | drafted, staged (not merged) | Classic quad half-H motor driver (distinct 16-pin part from existing `L298N`), half-bridge gate driver (`IR2104` - reused the exact `IR2110`/halfbridge role pattern verified against the live KG entry, not approximated), positive/negative 12V linear regs (first negative-output regulator in the KG), simple Schottky diode, bidirectional TVS diode (named `A1`/`A2`, no fixed polarity - not the same as the all-unnamed-pin risk class). Checked and deferred `XLR3` (3 unnamed pins with real distinguishing roles per standard XLR wiring - shield/hot/cold) and `MOC3020M` (opto-triac, unnamed functional pins) per the established exception rule |
| 21 | `TPS3808DBV`, `PT100`, `BPW34-SMD`, `MCP73831-2-MC`, `AP2112K-1.8` | drafted, staged (not merged) | Voltage supervisor/reset IC (new subcategory), 2-wire RTD temp sensor (symmetric 2-terminal exception applies), photodiode (named K/A, diode roles), simpler single-cell battery charger (complements existing `MCP73871`), 1.8V LDO (same family/pinout as existing `AP2112K-3.3`, different fixed voltage). **Self-caught error**: first draft of `AP2112K-1.8` had its pin numbers/names completely scrambled from memory instead of read from the pool - caught before finalizing by re-reading the real pool data and the existing `AP2112K-3.3` entry, corrected to the real layout (`VIN`/`GND`/`EN`/`NC`/`VOUT`) before saving |
| 22 | `MAX31855KASA`, `LM339`, `TL082`, `LM4040DBZ-2.5`, `REF02AP`, `SN74LVC245APW`, `FAN3111C` | drafted, staged (not merged) | K-type thermocouple SPI interface, quad comparator (reused `LM393`'s unnamed-output-pin precedent for 4 channels), dual JFET op-amp (reused `LM358`/`TL072`'s pattern), 2-terminal shunt voltage reference (complements 3-terminal `TL431DBV`), 3-terminal precision reference (`REF02AP` - genuinely different topology from the shunt reference, not redundant), 8-bit bus transceiver (distinct function from existing `TXS0108EPW` level translator), single-channel low-side gate driver (complements existing half-bridge `IR2110`/`IR2104`/`UCC27211`). Verified `gate_lo` role choice against `_check_bootstrap_caps` source directly before using it - that check only fires when BOTH `halfbridge_hb` and `halfbridge_hs` roles are present together, so a lone `gate_lo` on a non-half-bridge part doesn't risk a false bootstrap-cap requirement. Checked `ESP8266EX` (bare WiFi SoC) and deliberately did not add it - genuinely new but meaningfully higher-risk (needs correct crystal/decoupling/antenna-matching support circuitry to be a real, complete design; redundant in spirit with the module-level ESP parts already covered for vague-prompt purposes). Checked `ASSR-1218` solid-state relay - all 4 pins unnamed with real distinguishing roles, correctly deferred per the established relay/optocoupler exception. |
| 23 | `ADS1118IDGS`, `MCP1700x-330xxTO`, `IRLB8721PBF`, `S8050`, `S8550` | drafted, staged (not merged) | SPI ADC with internal ref/temp sensor (complements `MCP3008` - different channel count/feature set, not redundant), micropower 3.3V LDO (complements existing LDO family with a very-low-quiescent-current option), power N-MOSFET (complements `IRLZ44N`/`IRF540N` with different specs), classic common NPN/PNP pair (`S8050`/`S8550`). Checked `74HC02` (quad NOR, 12/14 pins unnamed) - deferred per the established rule; `LM555xMM`/`LM555xM`/`LM555xN` all checked and skipped as redundant package variants of already-curated `NE555D` (same pattern as `NE555P` caught in batch 11). |
| 24 | `Motor_Servo`, `ULN2004A`, `MCP41010`, `74LS138`, `MCP23008-xP`, `DAC081C081CIMK` | drafted, staged (not merged) | RC servo motor (genuinely new, common target for vague prompts), CMOS-input Darlington array (complements TTL-input `ULN2003A`/`ULN2804`, real functional distinction not just a rename), SPI digital potentiometer (new subcategory), 3-to-8 decoder (new logic function), 8-bit I2C IO expander (simpler alternative to existing 16-bit `MCP23017_SO`), I2C 8-bit DAC. All pin_roles matched exactly against existing precedent (`ULN2003A`'s I/O/COM pattern reused verbatim for `ULN2004A`). Checked and deferred `Barrel_Jack_Switch` (3 unnamed pins with real distinguishing function - tip/sleeve/switch - same defer rule as relays, not the symmetric-2-terminal exception) and `PESD3V3L4UF` (ESD diode array with a common-anode topology spanning 2 physical pins - doesn't cleanly fit the existing `supply_pair`-based ESD convention seen on `PESD4USB5U-TTS`, deferred rather than guess a constraint shape). |
| 25 | `PCF8563T`, `XBee_SMT`, `PCF8591`, `HLK-PM01`, `LM7806_TO220`, `LM7808_TO220`, `ESP32-S3-WROOM-1` | drafted, staged (not merged) | 2nd I2C RTC chip family (NXP, complements Maxim `DS1307+`/`DS3231MZ`), Zigbee RF module (new subcategory, dual/multi-function pin names like `DIO8/SLEEP_REQUEST` kept verbatim - same pattern already accepted on `SX1278`/`DAC80502`), 4ch-ADC+1-DAC combo IC (new subcategory), first isolated AC/DC power module in the KG, 6V/8V members of the already-curated 78xx linear-regulator family, a 2nd ESP32-S3 module variant (genuinely different pinout/package from the already-curated `ESP32-S3-MINI-1U`). `ESP32-S3-WROOM-1`'s GPIO roles matched exactly against the existing `ESP32-WROOM-32` convention (`logic_in`, not `logic_io`) rather than assumed. |
| 26 | `DRV8871DDA`, `TMP100`, `MCP9700Ax-ELT`, `AD9833xRM` | drafted, staged (not merged) | Single-channel brushed-DC motor driver with current limiting (distinct from the dual/half-bridge drivers already curated), 2nd I2C digital temp sensor family, simple analog thermistor-style temp sensor (cheaper/simpler alternative to `LM35-D`/`TMP36xS`), first programmable waveform generator in the KG (3-wire SPI-like control). |
| 27 | `MT3608`, `ADG728`, `UC3842_DIP8`, `SN74LVC1T45DBV`, `TLP250` | drafted, staged (not merged) | 2nd boost regulator (distinct pinout from `TPS61040DBV`), I2C 8:1 analog mux (new `analog_mux` subcategory), discrete PWM controller IC (new `pwm_controller` subcategory, for building a regulator from discrete parts rather than a module), single-bit level translator (simpler option alongside 8-bit `TXS0108EPW`), isolated gate-drive optocoupler (new `gate_driver_isolated` subcategory, distinct from non-isolated `IR2110`/`IR2104`) |
| 28 | `OPA2340`, `ATmega328-A`, `PIC16F1454-IP`, `CH340G`, `CD74HC4067M` | drafted, staged (not merged) | Dual rail-to-rail op-amp (verified structurally identical to already-proven `LM358` dual-unit pattern - safe, not the genuine ambiguity that caused batch 27 to skip 2 other op-amps), bare ATmega328 chip (distinct from `Arduino_UNO_R3` devboard and already-curated `ATmega32A-P`/`ATmega328P-PU`), PIC16F MCU with native USB (new family), 2nd USB-UART bridge (`CH340G`, confirmed different real pinout from live KG's `CH340C` by diffing pins directly), 16-channel analog mux (complements already-drafted 8-channel `ADG728`) |
| 29+ | TBD | pending | Continue in background while GPU is busy with validation. |

### Two more real duplicates caught this round (verified by diffing actual pin data, not just ids)
- **`MAX3232` skipped** - identical 16-pin layout/names to already-drafted `MAX232I` (well-known pin-compatible RS-232 transceiver family, same real pinout).
- **`MAX485E` skipped** - identical 8-pin layout/names to already-drafted `SP3485EN` (industry-standard second-source RS-485 pinout, same real pinout).
- Relay candidates checked again (`Relay_SPDT`, `G5LE-1`) - both still fully unnamed-pin with no fallback, correctly deferred per the standing rule.

### Two real duplicates found and fixed this round (verified by diffing actual pin data, not just ids)
- **`MCP4921-ESN` (batch 16) removed** - same real chip as the already-curated `MCP4921` (identical function, near-identical pins just with `VrefA`/`AVSS`/`VoutA` vs `Vref`/`Vss`/`Vout` naming - same part, not a different one).
- **`TPS3808DBV` (batch 21) removed** - exact duplicate of the already-curated `TPS3808` (byte-identical pin layout and function, package-suffix name only).
- The previously-flagged `Pololu_Breakout_DRV8825` (batch 17) vs. live `POLOLU_DRV8825` duplicate (same board, conflicting pinouts) was already fixed in a prior pass - confirmed still correctly removed, not re-added.
- **Lower-value (not a correctness duplicate) skip, for the record**: `Si7020-A20` has a byte-identical pinout to the already-drafted `Si7021-A20` - a real, different chip, but zero wiring-diversity value over keeping just one, so not added. `MCP41050` (same pinout as already-drafted `MCP41010`, different resistance value only) was similarly skipped as low marginal value, distinct from the `LM78xx` family case where output *voltage* is a primary, commonly-stated selection criterion in a vague prompt.
- Retry note (unchanged from prior entry): one fork attempt for batch 18 (2026-10-02) did zero real work and just echoed back a status phrase instead of executing - caught by checking the filesystem directly before trusting the report. Worth double-checking any fork's claimed output against the filesystem before taking it at face value.

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
- **Fixed a real duplicate caught by batch 24's fork and verified directly**:
  batch 17's `Pololu_Breakout_DRV8825` is the same real Pololu DRV8825
  breakout board already curated in the live KG as `POLOLU_DRV8825` - but
  with completely conflicting pin numbering between the two (verified by
  diffing both entries' real pin data). Removed the batch 17 duplicate
  entirely rather than keep two versions of the same board with different
  pinouts. The live KG's already-curated version is authoritative. Note:
  the concurrently-running live-test harness (launched before this fix)
  will still test the now-removed duplicate once - harmless, just one
  wasted test slot, not a correctness issue for anything that gets merged.
