# open-knx-valve-control

This is a controller for up to 8 underfloor heating actuators like [HmIP-FALMOT-C12](https://homematic-ip.com/en/product/valve-drive-motorised) to be integrated into the KNX bus. The Controller is based on the [STRKNX](https://www.st.com/en/interfaces-and-transceivers/stknx.html) and [ATTINY3216](https://www.microchip.com/en-us/product/attiny3216) with an `230V` supply voltage.

## BOM-List

The follwing is the BOM-List of all parts required for assembly and the order-number at [Mouser](http://mouser.com).

| Name              | Footprint     |	Quantity | Mouser No.      |
| ------------------| ------------- | ----- | -------------------- |
| 4.7uF	            | C0603         | 1 	| C1608X5R1V475K080AC |
| 100nF	            | C0603         | 18	| CC0603KRX5R9BB104 |
| 470nF	            | C0603         | 1 	| UMK107ABJ474KA-T |
| 10uF	            | C0603         | 11	| GRM188R6YA106MA73D |
| 47nF	            | C0603         | 2	    | CL10B473KB8NFNC |
| 1nF	            | C0603         | 2	    | 0603B102M500CT |
| 100uF	            | SMD,D8xL10mm	| 1	    | 107SML050M |
| 22uF	            | C0603	        | 2	    | CL10A226MO7JZNC |
| 22nF	            | C0603	        | 2	    | 06035C223K4T4A |
| SS34	            | SMA(DO-214AC)	| 2	    | SS34-HF |
| CPDH3V3UP-HF	    | SOD-523	    | 1	    | CPDH3V3UP-HF |
| P4SMAJ5.0A	    | SMA(DO-214AC)	| 1	    | P4SMAJ5.0A |
| SMAJ40CA-13-F	    | DO-214AC(SMA)	| 1	    | SMAJ40CA-13-F |
| 1N4148WS	        | SOD-323F	    | 3	    | 1N4148WS |
| 10kΩ Potentiometers |	SMD-3P,4.5x4.5mm | 1| 3314G-1-103E |
| IDC Connectors	| P=2.54mm, 2x3P	 | 2| 2-1761603-1 |
| 33uH	            | SMD,4.9x4.9mm	     | 1| NR5040T330M |
| LED Green	        | L0603	        | 2	   |  LTST-C190GKT |
| LED Blue	        | L0604	        | 3	   |  LTST-C194TBKT |
| LED Red	        | L0605	        | 2	   |  LTST-C190EKT |
| LED Yellow       	| L0606	        | 1	   |  LTST-C190KSKT |
| LED White	        | L0607	        | 8	   |  LTW-C191TLA |
| BC817	            | SOT-23-3	    | 1	   |  BC817-40-TP |
| 4.7MΩ	            | R0603	        | 1	   |  CRCW02014M70FNED |
| 470Ω	            | R0603	        | 15	| RC0201FR-13470RL |
| 10kΩ	            | R0402	        | 11	| CRGCQ0402F10K |
| 1kΩ	            | R0402	        | 1	   |  CRCW04021K00FKEE |
| 1kΩ	            | R0603	        | 2	   |  RC0201FR-071KP |
| 110kΩ	            | R0603	        | 1	   |  RC0201FR-07110KL |
| 10kΩ	            | R0603	        | 1	   |  CR0201AFW-1002GAS |
| 2.2kΩ	            | R0603	        | 1	   |  CRCW02012K20FNED |
| 4.7kΩ	            | R0603	        | 10	| CR0201-JW-472GLF |
| 200mΩ	            | R1206	        | 1	   |  SCR1206F1M1 |
| 10Ω	            | R0603	        | 2	   |  CR0201-JW-100GLF |
| 68Ω	            | R2512	        | 1	   |  CRGP2512F68R |
| EC11G1574402	    | PCB Mount	    | 1	   |  EC11G1574402 |
| 2P Screw Terminal	| Through Hole P=5.08mm	| 11	| TB006-508-02BE | 
| 3P Screw Terminal	| Through Hole P=5.08mm	| 10	| TB006-508-03BE |
| TSR 1-2433E	    | Through Hole	| 1	   |  TSR 1-2433E |
| IRM-02-5	        | Through Hole	| 1	   |  IRM-02-5 |
| STKNXTR	        | VFQFPN-24	    | 1	   |  STKNXTR |
| ATTINY3216	    | SOIC-20	    | 2	   |  ATTINY3216-SNR |
| INA219AIDR	    | SOIC-8	    | 1	   |  INA219AIDR |
| PCF8574	        | SOIC-16	    | 2	   |  PCF8574DWR |
| TB6612FNG,C,8,EL	| SSOP-24	    | 4	   |  TB6612FNG,C,8,EL |
