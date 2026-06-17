# Bill of Materials — AlohaMini2

AlohaMini2 follows the same Client/Host architecture as LeKiwi:

- **Host** — mobile base + follower arms + compute (Raspberry Pi 5)
- **Client** — PC workstation + leader arms

> Common tools (table clamp, soldering iron, screwdriver set) are not listed.

---

## Mobile Base

| Item | Spec | Qty | Unit ($) | Buy (US) | Unit (¥) | Buy (CN) |
|------|------|----:|---------:|----------|--------:|----------|
| Servo — STS-3215 (wheel) | ST-3215-C018, 12V, 1/345 gear | 3 | $15.97 | [Alibaba](https://www.alibaba.com/product-detail/Lerobot-360-Degree-Smart-Servo-for_1601563310522.html) | ¥110 | [Taobao](https://e.tb.cn/h.64H9u3maGWzIp5Q?tk=T5liexkG6Yz) |
| Servo — STS-3095 (lift) | ST-3095-C002, 12V, 95 kg·cm | 1 | $50.37 | [Alibaba](https://www.alibaba.com/product-detail/FEETECH-STS3095-12V-95KG-servo-AI_1601045980686.html) | ¥345 | [Taobao](https://item.taobao.com/item.htm?abbucket=18&id=764857479703) |
| Omni wheel | 127 mm (74A) | 3 | $40 | [omniawheel.com](https://www.omniawheel.com/) | ¥289 | [Taobao](http://e.tb.cn/h.R5jm5Xlk56vjQRJ) |
| Aluminum extrusion (T-frame) | 20×40×2 mm, L=400 mm *(or print `O_T_Connector_Cross_Bar.stl`)* | 1 | ~$1.50 | — | ¥10 | — |
| Steel pin (chassis) | Φ12×80 mm *(or print `O_Chassis_Dowel_Pin_12_80.stl`)* | 3 | ~$0.50 | Amazon | ¥3.28 | [Taobao](https://e.tb.cn/h.ivppuOirL8K8zsH?tk=IKNy5kRfNCm) |
| Steel pin (lift axis) | Φ12×25 mm *(or print `O_T_Connector_Dowel_Pin_12_25.stl`)* | 1 | ~$0.50 | Amazon | ¥3.28 | [Taobao](https://e.tb.cn/h.ivppuOirL8K8zsH?tk=IKNy5kRfNCm) |
| Bearing — lift track | 4×13×5 mm | 8 | ~$0.40 | Amazon | ¥3 | [Taobao](https://item.taobao.com/item.htm?id=565418362178) |
| Bearing — chassis/arm/lift | 12×18×4 mm | 8 | ~$0.80 | [Amazon](https://www.amazon.com/XIKE-6701-2RS-Bearings-12x18x4mm-Pre-Lubricated/dp/B09D2RQ4Y1) | ¥6 | [Tmall](https://detail.tmall.com/item.htm?id=824704356695) |
| Camera — front | H65V1, 720p, 2.4 mm, 1 m cable | 1 | ~$17 | Amazon | ¥122 | [Taobao](https://item.taobao.com/item.htm?id=666278411821) |
| Camera — back | H65V1, 720p, 2.4 mm, 1 m cable | 1 | ~$17 | Amazon | ¥122 | [Taobao](https://item.taobao.com/item.htm?id=666278411821) |
| Camera — chest | H65V1, 720p, 2.4 mm, 2 m cable | 1 | ~$17 | Amazon | ¥122 | [Taobao](https://item.taobao.com/item.htm?id=666278411821) |
| Raspberry Pi 5 | 2 GB RAM | 1 | ~$93 | [Adafruit](https://www.adafruit.com/product/5812) | ¥669 | [Taobao](https://item.taobao.com/item.htm?id=688878446695) |
| DC buck converter | 12V→5V 5A (PD protocol) | 1 | ~$9 | [Amazon](https://www.amazon.com/Klnuoxj-Converter-Interface-Waterproof-Compatible/dp/B0CRVW7N2J) | ¥66 | [Taobao](https://item.taobao.com/item.htm?id=800698078303) |
| Heatsink | Raspberry Pi 5 (passive) | 1 | ~$2.50 | Amazon | ¥18 | [Taobao](https://item.taobao.com/item.htm?id=755560852039) |
| microSD card | 32 GB | 1 | ~$14 | Amazon | ¥99.9 | — |
| HDMI→Micro HDMI cable | 1 m, 4K60Hz | 1 | ~$1 | Amazon | ¥7 | [pinduoduo](https://mobile.yangkeduo.com/goods.html?ps=9DevREvDAj) |
| Bus servo controller | Waveshare Bus Servo Adapter A | 1 | $5.00 | [Waveshare](https://www.waveshare.com/bus-servo-adapter-a.htm) | ¥27 | [Tmall](https://detail.tmall.com/item.htm?id=738817173460) |
| Battery 12V | 11200 mAh, DC 5521 | 2 | ~$16 | [Amazon](https://www.amazon.com/KBT-Rechargeable-Connector-Replacement-Security/dp/B0C242DYT1/) | ¥114 | [Taobao](https://item.taobao.com/item.htm?id=890828103056) |
| DC splitter cable | 1-to-2, 30 cm | 1 | ~$0.60 | Amazon | ¥4.5 | [Taobao](https://e.tb.cn/h.ivLJNFtMOZ50iFx?tk=GN8V5ki58UN) |
| DC extension cable | 1 m | 2 | ~$0.30 | Amazon | ¥2.3 | [Taobao](https://e.tb.cn/h.iucAEva43LkxQz1?tk=INAY5k79Qyz) |
| Servo extension cable | 90 cm, Feetech 3-pin | 2 | ~$0.30 | [Alibaba](https://www.alibaba.com/product-detail/3P-5264-Interface-Bus-Actuator-Connection_1601635790774.html) | ¥2 | Feetech channel |
| 3D-printed parts | PLA/PETG/ABS, Bambu P2S | — | ~4 kg filament | — | — | `/AlohaMini2/hardware/mobile_base/stl/` |

---

## Follower Arms (×2)

Each arm: **6+1 DoF, 52 cm reach, 1 kg payload** — based on AM-ARM200.

| Item | Spec | Qty | Unit ($) | Buy (US) | Unit (¥) | Buy (CN) |
|------|------|----:|---------:|----------|--------:|----------|
| Servo — STS-3215 | ST-3215-C018, 12V, 1/345 gear | 8 | $15.97 | [Alibaba](https://www.alibaba.com/product-detail/Lerobot-360-Degree-Smart-Servo-for_1601563310522.html) | ¥110 | [Taobao](https://e.tb.cn/h.64H9u3maGWzIp5Q?tk=T5liexkG6Yz) |
| Servo — STS-3095 | ST-3095-C002, 12V, 95 kg·cm | 6 | $50.37 | [Alibaba](https://www.alibaba.com/product-detail/FEETECH-STS3095-12V-95KG-servo-AI_1601045980686.html) | ¥345 | [Taobao](https://item.taobao.com/item.htm?abbucket=18&id=764857479703) |
| Hex socket screw M3×10 | 100-pack | 2 packs | — | — | ¥6 | [Taobao](https://e.tb.cn/h.R0nMFj8y9riNyJl?tk=HNii5rHz4NJ) |
| Heat-set insert | M3×5×4 | 1 pack | — | Amazon | ¥5 | [Taobao](https://item.taobao.com/item.htm?id=809241671998) |
| Servo extension cable | SCS 3-pin, 26 cm | 12 | $0.43 | [AliExpress](https://www.aliexpress.com/item/1005008074862037.html) | ¥3 | [Taobao](https://item.taobao.com/item.htm?id=616460581906) |
| Camera — wrist | H65V1, 720p, 2.4 mm, 2 m cable | 2 | ~$17 | Amazon | ¥122 | [Taobao](https://item.taobao.com/item.htm?id=666278411821) |
| Bus servo controller | Waveshare Bus Servo Adapter A | 2 | $5.00 | [Waveshare](https://www.waveshare.com/bus-servo-adapter-a.htm) | ¥27 | [Tmall](https://detail.tmall.com/item.htm?id=738817173460) |
| USB Type-C cable | 1 m (arm → Pi 5) | 4 | — | — | ¥4.8 | [pinduoduo](https://mobile.yangkeduo.com/goods1.html?ps=fDPvH0kvgs) |
| 3D-printed parts | PLA/PETG/ABS, Bambu P2S | — | — | — | — | `/AlohaMini2/hardware/arms/stl/` |

---

## Leader Arms (×2)

| Item | Spec | Qty | Unit ($) | Buy (US) | Unit (¥) | Buy (CN) |
|------|------|----:|---------:|----------|--------:|----------|
| Servo — STS-3215 | ST-3215-C046, 7.4V, 1/147 gear | 14 | $15.97 | [Alibaba](https://www.alibaba.com/product-detail/Lerobot-360-Degree-Smart-Servo-for_1601563310522.html) | ¥110 | [Taobao](https://e.tb.cn/h.64H9u3maGWzIp5Q?tk=T5liexkG6Yz) |
| Heat-set insert | M3×5×4 | 1 pack | — | Amazon | ¥5 | [Taobao](https://item.taobao.com/item.htm?id=809241671998) |
| Bus servo controller | Waveshare | 2 | $12.47 | [Amazon](https://www.amazon.com/Waveshare-Integrates-Control-Circuit-Supports/dp/B0CTMM4LWK/) | ¥27 | [Tmall](https://detail.tmall.com/item.htm?id=738817173460) |
| Power supply 5V | DC 5V AC adapter | 1 | $12.99 | [Amazon](https://www.amazon.com/Facmogu-Switching-Transformer-Compatible-5-5x2-1mm/dp/B087LY41PV/) | — | — |
| USB Type-C cable | 1 m (arm → PC) | 2 | $7.19 | [Amazon](https://www.amazon.com/Charging-etguuds-Charger-Braided-Compatible/dp/B0B8NWLLW2/) | ¥20 | [Tmall](https://detail.tmall.com/item.htm?id=754024805047) |
| DC splitter cable | 1-to-2, 70 cm | 1 | — | — | ¥6.5 | [Taobao](https://e.tb.cn/h.ivLJNFtMOZ50iFx?tk=GN8V5ki58UN) |
| 3D-printed parts | PLA/PETG/ABS, Bambu P2S | — | — | — | — | `/AlohaMini2/hardware/arms/stl/` |

---

## Fasteners & Consumables

| Item | Spec | Qty | Unit ($) | Buy (US) | Unit (¥) | Buy (CN) |
|------|------|----:|---------:|----------|--------:|----------|
| Heat-set insert M3 | M3×5×4 mm, 50-pack | 1 pack | ~$0.30 | Amazon | ¥2.2 | — |
| Hex socket screw M3×10 | 100-pack, blue thread-lock | 3 packs | ~$1.20 | — | ¥8.5 | — |
| Hex socket screw M3×18 | 50-pack | 1 pack | ~$0.65 | — | ¥4.72 | — |
| Epoxy adhesive | Loctite E-120HP 50 mL | 1 | ~$10 | Amazon | ¥74.9 | — |

---

## Total Estimate

| | CNY | USD |
|--|-----|-----|
| Mobile base | ¥2,475 | ~$344 |
| Follower arms | ¥3,320 | ~$461 |
| Leader arms | ¥1,646 | ~$277 |
| Fasteners & consumables | ¥107 | ~$15 |
| **Total (self-print)** | **¥7,548** | **~$1,097** |

> Filament cost (~5 kg) not included above 
