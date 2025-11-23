# apps/integrations/pricing_config.py

from typing import Dict, Any

SYSTEM_CONFIG = {
    # ===================== ФАЛЬШ-РОЛЕТИ =====================
    "Фальші": {
        "slug": "falshi",
        "comment_proportions": """За замовчуванням приймаються розміри: ширина по тканині, 
                                висота габаритна. Габаритна ширина виробу на 4мм більша за ширину по 
                                тканині (на товщину заглушки нижньої планки). Якщо потрібен габаритний 
                                розмір, Замовник повинен вказати це окремо.
                                """,
        "price_options":{
            "magnets_fixation":0.56    
        },
        # Всі системи в прайсі: висота вказується габаритна
        "default_height_dim": "gabarit",
        # Ціна рахується по ширині тканини, але можна вводити й габарит
        "width": {
            "base_dim": "fabric",  # прайс-бенди по тканині
            "input_modes": ["fabric", "gabarit"],  # що можна вводити в конструкторі
            # Як отримати базову ширину (по тканині) з того, що ввів користувач:
            # base_width_mm = entered_width_mm + to_base_from[input_mode]
            "to_base_from": {
                "fabric": 0,  # ввели по тканині → нічого не міняємо
                "gabarit": -4,  # габарит = тканина + 4мм → тканина = габарит - 4
            },
        },
        # “+10% за кожні 10см перевищення висоти”
        "surcharge": {
            "enabled": True,
            "threshold_dim": "gabarit",  # порівнюємо габаритну висоту з лімітом у колонці
            "per_100mm_pct": 10,
        },
        # В прайсі немає явної “макс. гарантійної ширини/висоти”
        "limits": {
            "max_width_mm": None,
            "max_height_mm": None,
        },
    },
    "Фальші DN": {
        "slug": "falshi_dn",
        "default_height_dim": "gabarit",
        "width": {
            "base_dim": "fabric",
            "input_modes": ["fabric", "gabarit"],
            # Габаритна ширина на 20мм більша за ширину по тканині
            "to_base_from": {
                "fabric": 0,
                "gabarit": -20,  # тканина = габарит - 20
            },
        },
        "surcharge": {
            "enabled": True,
            "threshold_dim": "gabarit",
            "per_100mm_pct": 10,
        },
        "limits": {
            "max_width_mm": None,
            "max_height_mm": None,
        },
    },
    # ===================== ВІДКРИТА 19-й Besta =====================
    "Відкр 19-й Besta": {
        "slug": "open_19_besta",
        "default_height_dim": "gabarit",
        "width": {
            # “За замовчуванням: ширина по тканині, висота габаритна”
            "base_dim": "fabric",
            "input_modes": ["fabric", "gabarit"],
            # “Габаритна ширина виробу на 35мм більша за ширину по тканині”
            "to_base_from": {
                "fabric": 0,
                "gabarit": -35,
            },
        },
        "surcharge": {
            "enabled": True,
            "threshold_dim": "gabarit",
            "per_100mm_pct": 10,
        },
        "limits": {
            "max_width_mm": 1300,
            "max_height_mm": 2000,
        },
    },
    "Відкр 19-й Besta DN": {
        "slug": "open_19_besta_dn",
        "default_height_dim": "gabarit",
        "width": {
            "base_dim": "fabric",
            "input_modes": ["fabric", "gabarit"],
            # той самий текст про +35мм
            "to_base_from": {
                "fabric": 0,
                "gabarit": -35,
            },
        },
        "surcharge": {
            "enabled": True,
            "threshold_dim": "gabarit",
            "per_100mm_pct": 10,
        },
        "limits": {
            "max_width_mm": 1300,
            "max_height_mm": 2000,
        },
    },
    # ===================== ЗАКР. ПЛОСКА Uni Besta =====================
    "Закрита Плоска Besta": {
        "slug": "closed_flat_besta",
        "default_height_dim": "gabarit",
        "width": {
            # “ширина і висота по зовнішнім краям штапіка”
            "base_dim": "shtapik",
            # В правилах, які ти надіслав:
            #   варіанти: по тканині / по штапіку
            #   за замовчуванням по штапіку
            #   якщо замір по тканині → +44мм до штапіка
            "input_modes": ["shtapik", "fabric"],
            "to_base_from": {
                "shtapik": 0,
                "fabric": +44,  # штапік = тканина + 44
            },
        },
        "surcharge": {
            "enabled": True,
            "threshold_dim": "gabarit",
            "per_100mm_pct": 10,
        },
        "limits": {
            "max_width_mm": 1300,
            "max_height_mm": 1700,
        },
    },
    "Закрита плоска Besta DN": {
        "slug": "closed_flat_besta_dn",
        "default_height_dim": "gabarit",
        "width": {
            "base_dim": "shtapik",
            "input_modes": ["shtapik", "fabric"],
            "to_base_from": {
                "shtapik": 0,
                "fabric": +44,
            },
        },
        "surcharge": {
            "enabled": True,
            "threshold_dim": "gabarit",
            "per_100mm_pct": 10,
        },
        "limits": {
            "max_width_mm": 1300,
            "max_height_mm": 1700,
        },
    },
    # ===================== ЗАКР. П-ПОДІБНА Uni Besta =====================
    "Закрита П-подіб Besta": {
        "slug": "closed_p_besta",
        "default_height_dim": "gabarit",
        "width": {
            # Базова ширина в прайсі — по зовнішнім краям штапіка
            "base_dim": "shtapik",
            "input_modes": ["shtapik", "gabarit"],
            # “Габаритна ширина на 20мм більша від ширини по зовнішнім краям штапіків”
            "to_base_from": {
                "shtapik": 0,
                "gabarit": -20,
            },
        },
        "surcharge": {
            "enabled": True,
            "threshold_dim": "gabarit",
            "per_100mm_pct": 10,
        },
        "limits": {
            "max_width_mm": 1300,
            "max_height_mm": 2000,
        },
    },
    "Закрита П-подібна Besta DN": {
        "slug": "closed_p_besta_dn",
        "default_height_dim": "gabarit",
        "width": {
            "base_dim": "shtapik",
            "input_modes": ["shtapik", "gabarit"],
            "to_base_from": {
                "shtapik": 0,
                "gabarit": -20,
            },
        },
        "surcharge": {
            "enabled": True,
            "threshold_dim": "gabarit",
            "per_100mm_pct": 10,
        },
        "limits": {
            "max_width_mm": 1300,
            "max_height_mm": 2000,
        },
    },
    # ===================== ВІДКР. 25-й Besta =====================
    "Відкр 25-й Besta": {
        "slug": "open_25_besta",
        "default_height_dim": "gabarit",
        "width": {
            "base_dim": "fabric",
            "input_modes": ["fabric", "gabarit"],
            # “Габаритна ширина виробу на 35мм більша за ширину по тканині”
            "to_base_from": {
                "fabric": 0,
                "gabarit": -35,
            },
        },
        "surcharge": {
            "enabled": True,
            "threshold_dim": "gabarit",
            "per_100mm_pct": 10,
        },
        "limits": {
            "max_width_mm": 2000,
            "max_height_mm": 2300,
        },
    },
    "Відкр 25-й DN": {
        "slug": "open_25_dn",
        "default_height_dim": "gabarit",
        "width": {
            "base_dim": "fabric",
            "input_modes": ["fabric", "gabarit"],
            # “Габаритна ширина виробу на 30мм більша за ширину по тканині”
            "to_base_from": {
                "fabric": 0,
                "gabarit": -30,
            },
        },
        "surcharge": {
            "enabled": True,
            "threshold_dim": "gabarit",
            "per_100mm_pct": 10,
        },
        "limits": {
            "max_width_mm": 2000,
            "max_height_mm": 2000,
        },
    },
    # ===================== ВІДКР. ПРУЖИННА =====================
    "Відкр Пружинна": {
        "slug": "open_spring_25",
        "default_height_dim": "gabarit",
        "width": {
            "base_dim": "fabric",
            "input_modes": ["fabric", "gabarit"],
            # текст: “Габаритна ширина виробу на 35мм більша за ширину по тканині”
            "to_base_from": {
                "fabric": 0,
                "gabarit": -35,
            },
        },
        "surcharge": {
            "enabled": True,
            "threshold_dim": "gabarit",
            "per_100mm_pct": 10,
        },
        "limits": {
            "max_width_mm": 1400,
            "max_height_mm": 2000,
        },
    },
    # ===================== ЗАКР. ПРУЖ. П-ПОДІБНА =====================
    "Закр Пруж П-подіб Besta": {
        "slug": "closed_spring_p_besta",
        "default_height_dim": "gabarit",
        "width": {
            "base_dim": "shtapik",
            "input_modes": ["shtapik", "gabarit"],
            # “Габаритна ширина на 20мм більша від ширини по зовнішнім краям штапіків”
            "to_base_from": {
                "shtapik": 0,
                "gabarit": -20,
            },
        },
        "surcharge": {
            "enabled": True,
            "threshold_dim": "gabarit",
            "per_100mm_pct": 10,
        },
        "limits": {
            "max_width_mm": 1400,
            "max_height_mm": 2000,
        },
    },
    # ===================== ВІДКР. 32-й Louvolitte =====================
    "Відкр 32-й Louvolitte": {
        "slug": "open_32_louvolitte",
        "default_height_dim": "gabarit",
        "width": {
            "base_dim": "fabric",
            "input_modes": ["fabric", "gabarit"],
            # у прайсі: “Габаритна ширина виробу на 35мм більша за ширину по тканині”
            "to_base_from": {
                "fabric": 0,
                "gabarit": -35,
            },
        },
        "surcharge": {
            "enabled": True,
            "threshold_dim": "gabarit",
            "per_100mm_pct": 10,
        },
        "limits": {
            "max_width_mm": 2500,
            "max_height_mm": 2500,
        },
    },
    # ===================== ВІДКР. 47-й, двигун або Louvolit =====================
    "Відкр 47-й, двигун або Louvolit": {
        "slug": "open_47_louvolitte_motor",
        "default_height_dim": "gabarit",
        "width": {
            "base_dim": "fabric",
            "input_modes": ["fabric", "gabarit"],
            # “Габаритна ширина виробу на 50мм більша за ширину по тканині”
            "to_base_from": {
                "fabric": 0,
                "gabarit": -50,
            },
        },
        "surcharge": {
            "enabled": True,
            "threshold_dim": "gabarit",
            "per_100mm_pct": 10,
        },
        "limits": {
            "max_width_mm": 3000,
            "max_height_mm": 3000,
        },
    },
}


def get_system_cfg(system_name: str) -> Dict[str, Any]:
    """
    EN: Return config for given system (sheet).
    UA: Повертає конфіг для вказаної системи (назва вкладки).
    """
    return SYSTEM_CONFIG.get(system_name) or {
        "slug": "default",
        "default_height_dim": "gabarit",
        "width": {
            "base_dim": "fabric",
            "input_modes": ["fabric"],
            "to_base_from": {"fabric": 0},
        },
        "surcharge": {
            "enabled": True,
            "threshold_dim": "gabarit",
            "per_100mm_pct": 10,
        },
        "limits": {
            "max_width_mm": None,
            "max_height_mm": None,
        },
        "extras": [],
    }
