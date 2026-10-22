# -*- coding: utf-8 -*-
"""
مشروع الفراغ — محرّك الحسابات (v6)

كل رقم في ملف النتائج يُحسب هنا من الثوابت الأساسية، لا يُكتب يدوياً.
تشغيل:  python3 calc.py           -> جدول كامل + results.json
"""
from __future__ import annotations

import json
import math

# ------------------------------------------------------------------ constants (SI)
c = 299_792_458.0
G = 6.674_30e-11
HBAR = 1.054_571_817e-34
PI = math.pi
M_SUN = 1.988_92e30
M_JUP = 1.898_13e27
LY = 9.460_730_472e15
AU = 1.495_978_707e11
YEAR = 3.155_760e7
L_SUN = 3.828e26            # W
R_UNIVERSE = 4.4e26         # m (comoving, approximate observable radius)
E_UNIVERSE = 4e69           # J (approximate, baryonic + dark, order of magnitude)

# Planck units
T_PL = math.sqrt(HBAR * G / c ** 5)
L_PL = math.sqrt(HBAR * G / c ** 3)
A_PL = c / T_PL
RHO_PL = c ** 5 / (HBAR * G ** 2)

# ------------------------------------------------------------------ derived laws
#
# 1) Morris-Thorne throat density (b' = 1):
#       rho = - c^4 / (8 pi G b^2)
# 2) Ford-Roman quantum inequality (sampling time T):
#       rho >= - 3 hbar / (32 pi^2 c^3 T^4)
# 3) Combining, |rho_req| <= |rho_QI|:
#       c^4/(8 pi G b^2) <= 3 hbar/(32 pi^2 c^3 T^4)
#   =>  b^2 >= 4 pi c^7 T^4 / (3 G hbar)
#   =>  b   >= k T^2 ,   k = sqrt(4 pi c^7 / (3 G hbar))
#
K_WINDOW = math.sqrt(4 * PI * c ** 7 / (3 * G * HBAR))     # m / s^2

# 4) exotic mass / energy for a throat of radius b
#       M = c^2 b / G ,  E = c^4 b / G
#
D_E_DB = c ** 4 / G                                        # J per metre

# 5) tidal bound
#       b >= (v/c) * c * sqrt(L / a_max)


def rho_throat(b: float) -> float:
    return -c ** 4 / (8 * PI * G * b ** 2)


def rho_qi(T: float) -> float:
    return -3 * HBAR / (32 * PI ** 2 * c ** 3 * T ** 4)


def t_max(b: float) -> float:
    return math.sqrt(b / K_WINDOW)


def b_for_time(T: float) -> float:
    return K_WINDOW * T ** 2


def exotic_mass(b: float) -> float:
    return c ** 2 * b / G


def exotic_energy(b: float) -> float:
    return c ** 4 * b / G


def casimir_pressure(d: float) -> float:
    """Ideal parallel plates, attractive: P = -pi^2 hbar c / (240 d^4)  [Pa]."""
    return -PI ** 2 * HBAR * c / (240 * d ** 4)


def casimir_density(d: float) -> float:
    """Energy density between the plates: rho = -pi^2 hbar c / (720 d^4)  [J/m^3].

    This is the quantity comparable with the throat requirement; the pressure is
    three times larger. Quoting pressure when the comparison is with an energy
    density overstates the Casimir side by a factor of 3.
    """
    return -PI ** 2 * HBAR * c / (720 * d ** 4)


def tidal_throat(L: float, v_over_c: float = 1.0, a_max: float = 10.0) -> float:
    return v_over_c * c * math.sqrt(L / a_max)


def body_extent(mass_kg: float, density: float = 1000.0) -> float:
    return (mass_kg / density) ** (1.0 / 3.0)


def cost_per_kg(mass_kg: float, density: float = 1000.0, v_over_c: float = 1.0,
                a_max: float = 10.0) -> float:
    b = tidal_throat(body_extent(mass_kg, density), v_over_c, a_max)
    return exotic_energy(b) / mass_kg


def sci(x: float, digits: int = 2) -> str:
    if x == 0:
        return "0"
    exp = int(math.floor(math.log10(abs(x))))
    mant = x / 10 ** exp
    return f"{mant:.{digits}f}e{exp}"


def sup(x: float) -> str:
    """Pretty 10^n with unicode superscripts (for the Arabic PDF)."""
    if x == 0:
        return "0"
    exp = int(math.floor(math.log10(abs(x))))
    mant = x / 10 ** exp
    table = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")
    return f"{mant:.2f}×10{str(exp).translate(table)}"


# ------------------------------------------------------------------ results
def build() -> dict:
    r = {}

    r["constants"] = {
        "c": c, "G": G, "hbar": HBAR,
        "t_planck": T_PL, "l_planck": L_PL, "a_planck": A_PL, "rho_planck": RHO_PL,
        "sun_lifetime_energy": L_SUN * 10e9 * YEAR,
    }

    r["window"] = {
        "k": K_WINDOW,
        "k_over_a_planck": K_WINDOW / A_PL,
        "formula": "b >= k*T^2 ,  k = sqrt(4*pi*c^7/(3*G*hbar))",
    }

    r["throat_table"] = []
    for label, b in [("بلانك", L_PL), ("1 nm", 1e-9), ("1 µm", 1e-6), ("1 mm", 1e-3),
                     ("1 m", 1.0), ("1 km", 1e3), ("1 AU", AU), ("1 ly", LY)]:
        r["throat_table"].append({
            "label": label, "b": b,
            "rho": rho_throat(b),
            "t_max": t_max(b),
            "light_crossing": b / c,
            "deficit": t_max(b) / (b / c),
            "mass": exotic_mass(b),
            "mass_sun": exotic_mass(b) / M_SUN,
            "mass_jup": exotic_mass(b) / M_JUP,
            "energy": exotic_energy(b),
            "energy_over_sun": exotic_energy(b) / (L_SUN * 10e9 * YEAR),
        })

    # the largest throat the visible universe can hold
    r["universe_cap"] = {
        "r_universe": R_UNIVERSE,
        "t_at_r_universe": t_max(R_UNIVERSE),
        "b_for_1ps": b_for_time(1e-12),
        "b_for_1ps_over_universe": b_for_time(1e-12) / R_UNIVERSE,
        "b_for_1ns_over_universe": b_for_time(1e-9) / R_UNIVERSE,
    }

    r["reverse"] = []
    for label, T in [("1 ps", 1e-12), ("1 ns", 1e-9), ("1 µs", 1e-6),
                     ("1 ms", 1e-3), ("1 s", 1.0), ("1 day", 86400.0), ("1 year", YEAR)]:
        b = b_for_time(T)
        r["reverse"].append({"label": label, "T": T, "b": b,
                             "b_over_universe": b / R_UNIVERSE})

    r["casimir"] = []
    for d in [1e-8, 1e-7, 1e-6, 1e-3]:
        r["casimir"].append({"d": d,
                             "p": casimir_pressure(d),
                             "rho": casimir_density(d),
                             "gap_to_1m_throat": abs(rho_throat(1.0)) / abs(casimir_density(d))})

    r["tidal"] = []
    for label, L, v in [("إنسان (سماكة)", 0.42, 1.0), ("إنسان (طول)", 1.8, 1.0),
                        ("مركبة 10 m", 10.0, 1.0), ("سفينة 100 m", 100.0, 1.0),
                        ("إنسان 0.1c", 0.42, 0.1), ("إنسان 0.01c", 0.42, 0.01)]:
        b = tidal_throat(L, v)
        r["tidal"].append({"label": label, "L": L, "v_over_c": v, "b": b,
                           "mass_sun": exotic_mass(b) / M_SUN,
                           "energy": exotic_energy(b),
                           "energy_over_sun": exotic_energy(b) / (L_SUN * 10e9 * YEAR)})

    r["economy"] = []
    for m in [70.0, 1e3, 1e6, 1e9]:
        b = tidal_throat(body_extent(m))
        r["economy"].append({"mass_kg": m, "extent_m": body_extent(m), "b": b,
                             "energy": exotic_energy(b), "cost_per_kg": exotic_energy(b) / m})

    # design scorecard: log10(required time / allowed time)
    r["scorecard"] = []
    for label, b, t_req in [("إنسان عبر عنق 1.3e8 m", tidal_throat(1.8), tidal_throat(1.8) / c),
                             ("ألكوبيير 10c (100 m)", 100.0, 100.0 / (10 * c)),
                             ("كراسنيكوف (1 km)", 1e3, 1e3 / c),
                             ("قشرة فيسر (1 m)", 1.0, 1.0 / c),
                             ("حلقة رومان (1 m, 1 s)", 1.0, 1.0)]:
        t_allow = t_max(b)
        gap = math.log10(t_req / t_allow)
        r["scorecard"].append({"label": label, "b": b, "t_req": t_req,
                               "t_allow": t_allow, "gap_log10": gap,
                               "verdict": max(0.0, 100.0 - 4.0 * gap)})

    return r


def main():
    r = build()
    print("=" * 74)
    print("مشروع الفراغ — النتائج المحسوبة")
    print("=" * 74)
    print(f"k (تسارع النافذة)        = {sci(r['window']['k'])} m/s^2")
    print(f"a_Planck                 = {sci(r['constants']['a_planck'])} m/s^2")
    print(f"k / a_Planck             = {r['window']['k_over_a_planck']:.3f}")
    print()
    print(f"{'throat':<10}{'rho (J/m3)':>14}{'Tmax (s)':>14}{'light t (s)':>14}{'Tmax/light':>14}")
    for row in r["throat_table"]:
        print(f"{row['label']:<10}{sci(row['rho']):>14}{sci(row['t_max']):>14}"
              f"{sci(row['light_crossing']):>14}{sci(row['deficit']):>14}")
    cap = r["universe_cap"]
    print(f"\nسقف الكون: جيب بنصف قطر الكون المرئي يبقى {sci(cap['t_at_r_universe'])} ثانية")
    print(f"           أي 1 ps يحتاج عنقاً = {cap['b_for_1ps_over_universe']:.1f} × نصف قطر الكون")
    print()
    print(f"{'T':>8}{'b required (m)':>18}{'b / universe':>16}")
    for row in r["reverse"]:
        print(f"{row['label']:>8}{sci(row['b']):>18}{sci(row['b_over_universe']):>16}")
    print()
    print("Casimir:")
    for row in r["casimir"]:
        print(f"  d={row['d']:.0e} m  rho={sci(row['rho'])} J/m3  P={sci(row['p'])} Pa"
              f"   gap to 1 m throat = {sci(row['gap_to_1m_throat'])}")
    print()
    print("Tidal:")
    for row in r["tidal"]:
        print(f"  {row['label']:<16} b={sci(row['b'])} m   M={sci(row['mass_sun'])} Msun")
    print()
    print("Scorecard:")
    for row in r["scorecard"]:
        print(f"  {row['label']:<24} gap=10^{row['gap_log10']:.1f}  score={row['verdict']:.0f}/100")
    with open("results.json", "w", encoding="utf-8") as fh:
        json.dump(r, fh, ensure_ascii=False, indent=2)
    print("\n-> results.json")


if __name__ == "__main__":
    main()
