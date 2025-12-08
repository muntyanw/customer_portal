from enum import Enum
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------
# Enum с именами листов (camelCase)
# ---------------------------------------------
class sheetName(str, Enum):
    falshi = "Фальші"
    falshiDn = "Фальші DN"
    vidkr19yiBesta = "Відкр 19-й Besta"
    vidkr19yiBestaDn = "Відкр 19-й Besta DN"
    zakrytaPloskaBesta = "Закрита Плоска Besta"
    zakrytaPloskaBestaDn = "Закрита плоска Besta DN"
    zakrytaPpodibBesta = "Закрита П-подіб Besta"
    zakrytaPpodibnaBestaDn = "Закрита П-подібна Besta DN"
    vidkr25yiBesta = "Відкр 25-й Besta"
    vidkr25yiDn = "Відкр 25-й DN"
    vidkrPruzhynna = "Відкр Пружинна"
    zakrPruzhPpodibBesta = "Закр Пруж П-подіб Besta"
    vidkr32yiLouvolitte = "Відкр 32-й Louvolitte"
    vidkr47yiDvyhunAboLouvolit = "Відкр 47-й, двигун або Louvolit"
    komplektatsiya = "Комплектація"


# ---------------------------------------------
# dataclass конфигурации
# ---------------------------------------------
@dataclass
class sheetConfig:
    gbDiffWidthMm: Optional[int] = None
    display: Optional[int] = 1
    exist_control_side: Optional[int] = 1


# ---------------------------------------------
# Глобальный словарь с конфигами
# ---------------------------------------------
sheetConfigs: dict[sheetName, sheetConfig] = {
    sheetName.falshi: sheetConfig(gbDiffWidthMm=4, exist_control_side=0),
    sheetName.falshiDn: sheetConfig(gbDiffWidthMm=20, exist_control_side=0),

    sheetName.vidkr19yiBesta: sheetConfig(gbDiffWidthMm=35),
    sheetName.vidkr19yiBestaDn: sheetConfig(gbDiffWidthMm=35),

    sheetName.zakrytaPloskaBesta: sheetConfig(gbDiffWidthMm=None),
    sheetName.zakrytaPloskaBestaDn: sheetConfig(gbDiffWidthMm=None),

    sheetName.zakrytaPpodibBesta: sheetConfig(gbDiffWidthMm=20),
    sheetName.zakrytaPpodibnaBestaDn: sheetConfig(gbDiffWidthMm=20),

    sheetName.vidkr25yiBesta: sheetConfig(gbDiffWidthMm=35),
    sheetName.vidkr25yiDn: sheetConfig(gbDiffWidthMm=30),

    sheetName.vidkrPruzhynna: sheetConfig(gbDiffWidthMm=35),
    sheetName.zakrPruzhPpodibBesta: sheetConfig(gbDiffWidthMm=20),

    sheetName.vidkr32yiLouvolitte: sheetConfig(gbDiffWidthMm=35),
    sheetName.vidkr47yiDvyhunAboLouvolit: sheetConfig(gbDiffWidthMm=50),

    sheetName.komplektatsiya: sheetConfig(gbDiffWidthMm=None, display = 0),
}


# ---------------------------------------------
# Поиск по строке названия листа
# ---------------------------------------------
def getConfigBySheetName(sheet_title: str) -> sheetConfig:
    for key, cfg in sheetConfigs.items():
        if key.value == sheet_title:
            return cfg
    raise KeyError(f"sheet config not found: {sheet_title}")
