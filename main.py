# -*- coding: utf-8 -*-
"""
CLICKER INFINITO - Juego incremental en Kivy puro (archivo unico).
Moneda: Puntos | Renacimientos | Super Renacimientos | Logros | Guardado automatico.
Toda la configuracion esta hardcodeada en la seccion CONFIG (sin entradas en runtime).
Compatible con Pydroid 3 y con Buildozer (build.yml).
"""
import json
import math
import os
import time

from kivy.app import App
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.utils import platform

# =====================================================================
# CONFIG
# =====================================================================
APP_TITLE = "Clicker Infinito"
SAVE_FILE = "clicker_infinito_save.json"
LOGIC_TICK = 0.1
UI_TICK = 0.25
AUTOSAVE_SECS = 10
DEV_WINDOW = (432, 936)  # solo fuera de Android (pruebas en PC)

BASE_CLICK = 1.0
MAX_NUM = 1e300
OFFLINE_MAX_HOURS = 8
OFFLINE_BASE_EFF = 0.10
OFFLINE_STEP = 0.10

MILESTONES = [25, 50, 100, 150, 200, 250, 300, 400, 500, 750, 1000]
MILESTONE_MULT = 2.0
MILESTONE_STEP = 0.25

# Renacimiento
REBIRTH_BASE = 1e5          # Puntos necesarios para el primer Renacimiento
REBIRTH_REQ_GROWTH = 8.0    # el requisito crece x8 por cada Renacimiento
REBIRTH_MULT = 2.0          # cada renacimiento: Puntos x2
PR_EXPONENT = 0.5           # PR = (1+renacimientos) * (Puntos/requisito)^0.5
PR_POWER = 1.5
PR_FORTUNE = 1.4
PR_CLICK = 2.0
PR_START_BASE = 1000.0
PR_START_MULT = 2.0
PR_DISCOUNT_STEP = 0.04
AUTOCLICK_PER = 1.0
SYN_STEP = 0.01
AUTOBUY_BUDGET = 0.5

# Super Renacimiento
SUPER_MIN_REBIRTHS = 20     # Renacimientos para el 1er Super
SUPER_MIN_STEP = 6          # +6 Renacimientos extra por cada Super hecho
SUPER_START_PR = 500.0
SUPER_START_GROWTH = 3.0
SUPER_MULT = 50.0           # Puntos x50 permanente por Super Renacimiento
SUPER_SP_DIV = 5            # SP = renacimientos // 5
SP_MULT_PER = 2.0
SP_PR_STEP = 0.5
SP_REQ_STEP = 0.20
SP_DISC_STEP = 0.10
AUTO_REBIRTH_FACTOR = 100.0

ACH_BONUS = 1.02

# (nombre, coste base, produccion/s base, crecimiento de coste)
GENS = [
    ("Cursor Automatico", 15, 0.1, 1.15),
    ("Abuelita", 100, 1, 1.15),
    ("Granja", 1100, 8, 1.15),
    ("Mina", 12000, 47, 1.15),
    ("Fabrica", 130000, 260, 1.15),
    ("Banco", 1.4e6, 1400, 1.15),
    ("Templo", 2e7, 7800, 1.15),
    ("Laboratorio", 3.3e8, 44000, 1.15),
    ("Portal", 5.1e9, 2.6e5, 1.15),
    ("Maquina del Tiempo", 7.5e10, 1.6e6, 1.15),
    ("Generador Cuantico", 1e12, 1e7, 1.15),
    ("Singularidad", 1.4e13, 6.5e7, 1.15),
]
# (propiedad requerida, multiplicador de coste base, multiplicador de produccion)
GEN_TIERS = [(1, 10, 2), (10, 100, 2), (25, 1e3, 3), (50, 1e4, 3), (100, 1e5, 5), (200, 1e6, 5)]
ROMAN = ["I", "II", "III", "IV", "V", "VI"]
CLICK_UPS = [("Dedo Fuerte", 100, 2), ("Guante de Hierro", 1e3, 2), ("Puno Cuantico", 1e4, 2),
             ("Mano de Dios", 1e5, 3), ("Clic Estelar", 1e6, 3), ("Clic Galactico", 1e8, 4),
             ("Clic Universal", 1e10, 5), ("Clic Infinito", 1e13, 10)]
G_UPS = [("Eficiencia I", 5e3, 1.5), ("Eficiencia II", 5e6, 1.5), ("Eficiencia III", 5e9, 2),
         ("Eficiencia IV", 5e12, 2), ("Eficiencia V", 5e15, 3), ("Eficiencia VI", 5e18, 3)]
S_UPS = [("Dedos Sinergicos I", 1e4), ("Dedos Sinergicos II", 1e7), ("Dedos Sinergicos III", 1e10),
         ("Dedos Sinergicos IV", 1e13), ("Dedos Sinergicos V", 1e16)]

# (id, nombre, descripcion, coste base, crecimiento, nivel max (0 = ilimitado))
PR_UPS = [
    ("pr_power", "Poder de Puntos", "Puntos x1.5 por nivel", 2, 2.5, 0),
    ("pr_fortune", "Fortuna de Renacimiento", "PR ganados x1.4 por nivel", 3, 2.8, 0),
    ("pr_click", "Clic Reforzado", "Poder de clic x2 por nivel", 2, 3.0, 0),
    ("pr_start", "Capital Inicial", "Empiezas cada Renacimiento con Puntos", 5, 3.0, 12),
    ("pr_discount", "Descuento Mayorista", "Generadores -4% de coste por nivel", 10, 2.2, 20),
    ("pr_autoclick", "Auto-Clicker", "+1 clic automatico por segundo", 8, 2.5, 20),
    ("pr_autobuy", "Auto-Comprador", "Compra generadores automaticamente", 50, 1.0, 1),
    ("pr_milestone", "Hitos Mejorados", "Bonus de hitos +0.25 por nivel", 20, 2.5, 8),
    ("pr_offline", "Trabajo Nocturno", "Progreso offline +10% por nivel", 4, 2.0, 9),
    ("pr_synergy", "Sinergia de Clic", "Clic suma +1% de Puntos/s por nivel", 6, 2.4, 25),
]
SP_UPS = [
    ("sp_mult", "Super Multiplicador", "Puntos x2 por nivel (permanente)", 1, 2.2, 0),
    ("sp_pr", "Reservas de Renacimiento", "+50% PR iniciales tras Super", 1, 2.0, 0),
    ("sp_req", "Renacer Veloz", "Requisito de Renacimiento -20%", 3, 2.0, 10),
    ("sp_discount", "Super Descuento", "Coste de generadores -10%", 3, 2.5, 10),
    ("sp_autorebirth", "Auto-Renacimiento", "Renace solo cuando conviene", 5, 1.0, 1),
]
PR_DEF = dict((u[0], u) for u in PR_UPS)
SP_DEF = dict((u[0], u) for u in SP_UPS)

SUFFIXES = ["", "K", "M", "B", "T", "Qa", "Qi", "Sx", "Sp", "Oc", "No", "Dc"]

BG = (0.06, 0.07, 0.11, 1)
PANEL = (0.12, 0.14, 0.21, 1)
PANEL2 = (0.18, 0.20, 0.29, 1)
ACCENT = (0.22, 0.52, 0.95, 1)
GOLD = (1, 0.80, 0.25, 1)
GREEN = (0.15, 0.62, 0.35, 1)
PURPLE = (0.55, 0.30, 0.90, 1)
RED = (0.75, 0.25, 0.25, 1)
ORANGE = (0.90, 0.55, 0.10, 1)
DISABLED = (0.24, 0.26, 0.33, 1)


# =====================================================================
# UTILIDADES
# =====================================================================
def fmt(n):
    try:
        n = float(n)
    except Exception:
        return "0"
    if n != n:
        return "0"
    if n >= MAX_NUM:
        return "MAX"
    if n < 0:
        return "-" + fmt(-n)
    if n < 1000:
        if abs(n - round(n)) < 0.005:
            return str(int(round(n)))
        return ("%.2f" % n) if n < 10 else ("%.1f" % n)
    e = int(math.floor(math.log10(n) / 3))
    v = n / (1000.0 ** e)
    if round(v, 2) >= 1000:
        e += 1
        v /= 1000.0
    if e < len(SUFFIXES):
        return "%.2f%s" % (v, SUFFIXES[e])
    ex = int(math.floor(math.log10(n)))
    return "%.2fe%d" % (n / (10 ** ex), ex)


def fmt_time(s):
    s = int(s)
    h = s // 3600
    m = (s % 3600) // 60
    if h >= 24:
        return "%dd %dh" % (h // 24, h % 24)
    if h:
        return "%dh %dm" % (h, m)
    return "%dm %ds" % (m, s % 60)


# =====================================================================
# LOGROS
# =====================================================================
ACHS = []


def _ach(aid, name, desc, fn):
    ACHS.append((aid, name, desc, fn))


for _n, _nm in [(1, "Primer Toque"), (100, "Dedos Agiles"), (1000, "Maniaco del Clic"),
                (10000, "Clic sin Fin"), (100000, "Dedo de Titanio")]:
    _ach("clk%d" % _n, _nm, "Haz %s clics" % fmt(_n), lambda g, n=_n: g.clicks >= n)
for _n, _nm in [(1e3, "Ahorrador"), (1e6, "Millonario"), (1e9, "Magnate"), (1e12, "Titan"),
                (1e18, "Leyenda"), (1e30, "Dios de los Puntos"), (1e60, "Mas Alla")]:
    _ach("pts%d" % int(math.log10(_n)), _nm, "Acumula %s Puntos en total" % fmt(_n),
         lambda g, n=_n: g.lifetime >= n)
for _n, _nm in [(1, "Nueva Vida"), (5, "Ciclo Eterno"), (10, "Rueda del Destino"), (25, "Alma Antigua")]:
    _ach("reb%d" % _n, _nm, "Renace %d veces en total" % _n, lambda g, n=_n: g.total_rebirths >= n)
for _n, _nm in [(1, "Trascendencia"), (3, "Ascendido"), (10, "Divinidad")]:
    _ach("sup%d" % _n, _nm, "Haz %d Super Renacimiento(s)" % _n, lambda g, n=_n: g.supers >= n)
for _n, _nm in [(50, "Coleccionista"), (250, "Imperio"), (1000, "Industria Total")]:
    _ach("own%d" % _n, _nm, "Ten %d generadores a la vez" % _n, lambda g, n=_n: g.total_owned() >= n)
for _n, _nm in [(1e3, "Maquina Aceitada"), (1e6, "Rio de Puntos"), (1e9, "Cascada"), (1e12, "Big Bang")]:
    _ach("pps%d" % int(math.log10(_n)), _nm, "Produce %s Puntos/s" % fmt(_n), lambda g, n=_n: g.pps >= n)


# =====================================================================
# LOGICA DEL JUEGO
# =====================================================================
class Game:
    def __init__(self):
        self.msgs = []
        self.reset_all()

    # ---------- estado ----------
    def reset_all(self):
        self.points = 0.0
        self.run_points = 0.0
        self.lifetime = 0.0
        self.clicks = 0
        self.owned = [0] * len(GENS)
        self.ups = set()
        self.rebirths = 0
        self.total_rebirths = 0
        self.pr = 0.0
        self.pr_ups = {}
        self.supers = 0
        self.sp = 0.0
        self.sp_ups = {}
        self.ach = set()
        self.auto_buy = False
        self.auto_rebirth = False
        self.play_time = 0.0
        self._t_auto = 0.0
        self._t_ach = 0.0
        self.pps = 0.0
        self.gmult = 1.0
        self.click_val = 1.0
        self.recalc()

    def reset_run(self, start_points=0.0):
        self.points = float(start_points)
        self.run_points = 0.0
        self.owned = [0] * len(GENS)
        self.ups = set()

    def lvl(self, uid):
        return self.pr_ups.get(uid, 0)

    def slvl(self, uid):
        return self.sp_ups.get(uid, 0)

    def total_owned(self):
        return sum(self.owned)

    # ---------- multiplicadores ----------
    def disc(self):
        return ((1 - PR_DISCOUNT_STEP) ** self.lvl("pr_discount")) * ((1 - SP_DISC_STEP) ** self.slvl("sp_discount"))

    def perm_mult(self):
        m = REBIRTH_MULT ** min(self.rebirths, 900)
        m *= PR_POWER ** self.lvl("pr_power")
        m *= SUPER_MULT ** min(self.supers, 150)
        m *= SP_MULT_PER ** self.slvl("sp_mult")
        m *= ACH_BONUS ** len(self.ach)
        return min(m, MAX_NUM)

    def global_mult(self):
        m = self.perm_mult()
        for i, u in enumerate(G_UPS):
            if "a%d" % i in self.ups:
                m *= u[2]
        return min(m, MAX_NUM)

    def milestone_mult(self):
        return MILESTONE_MULT + MILESTONE_STEP * self.lvl("pr_milestone")

    def gen_mult(self, i):
        cnt = sum(1 for m in MILESTONES if self.owned[i] >= m)
        m = self.milestone_mult() ** cnt
        for t, tier in enumerate(GEN_TIERS):
            if "g%d_%d" % (i, t) in self.ups:
                m *= tier[2]
        return m

    def unit_rate(self, i):
        return GENS[i][2] * self.gen_mult(i) * self.gmult

    def next_milestone(self, i):
        for m in MILESTONES:
            if self.owned[i] < m:
                return m
        return 0

    def recalc(self):
        self.gmult = self.global_mult()
        total = 0.0
        for i, g in enumerate(GENS):
            total += self.owned[i] * g[2] * self.gen_mult(i)
        self.pps = min(total * self.gmult, MAX_NUM)
        cm = BASE_CLICK * (PR_CLICK ** self.lvl("pr_click"))
        for i, u in enumerate(CLICK_UPS):
            if "c%d" % i in self.ups:
                cm *= u[2]
        syn = SYN_STEP * self.lvl("pr_synergy")
        for i in range(len(S_UPS)):
            if "s%d" % i in self.ups:
                syn += SYN_STEP
        self.click_val = min(cm * self.gmult + self.pps * syn, MAX_NUM)

    # ---------- puntos ----------
    def add_points(self, x):
        self.points = min(self.points + x, MAX_NUM)
        self.run_points = min(self.run_points + x, MAX_NUM)
        self.lifetime = min(self.lifetime + x, MAX_NUM)

    def click(self):
        self.clicks += 1
        self.add_points(self.click_val)
        return self.click_val

    # ---------- generadores ----------
    def gen_cost(self, i, n=1):
        _, base, _, gr = GENS[i]
        return base * (gr ** self.owned[i]) * (gr ** n - 1) / (gr - 1) * self.disc()

    def max_buy(self, i):
        _, base, _, gr = GENS[i]
        first = base * (gr ** self.owned[i]) * self.disc()
        if self.points < first:
            return 0
        n = int(math.log(self.points * (gr - 1) / first + 1) / math.log(gr))
        while n > 0 and self.gen_cost(i, n) > self.points:
            n -= 1
        return n

    def buy_gen(self, i, mode):
        n = self.max_buy(i) if mode == 0 else mode
        if n <= 0:
            return False
        c = self.gen_cost(i, n)
        if c > self.points:
            return False
        self.points -= c
        self.owned[i] += n
        self.recalc()
        return True

    # ---------- mejoras normales ----------
    def available_upgrades(self):
        out = []
        for i, u in enumerate(CLICK_UPS):
            if "c%d" % i not in self.ups:
                out.append(("c%d" % i, u[0], "Poder de clic x%s" % fmt(u[2]), u[1]))
                break
        for i, u in enumerate(G_UPS):
            if "a%d" % i not in self.ups:
                out.append(("a%d" % i, u[0], "Todos los Puntos x%s" % fmt(u[2]), u[1]))
                break
        for i, u in enumerate(S_UPS):
            if "s%d" % i not in self.ups:
                out.append(("s%d" % i, u[0], "Cada clic suma +1% de tus Puntos/s", u[1]))
                break
        for gi, g in enumerate(GENS):
            for t, tier in enumerate(GEN_TIERS):
                uid = "g%d_%d" % (gi, t)
                if uid in self.ups:
                    continue
                if self.owned[gi] >= tier[0]:
                    out.append((uid, "%s %s" % (g[0], ROMAN[t]), "Produccion de %s x%s" % (g[0], fmt(tier[2])),
                                g[1] * tier[1]))
                break
        out.sort(key=lambda u: u[3])
        return out

    def buy_up(self, uid):
        for u in self.available_upgrades():
            if u[0] == uid:
                if self.points < u[3]:
                    return False
                self.points -= u[3]
                self.ups.add(uid)
                self.recalc()
                return True
        return False

    # ---------- renacimiento ----------
    def rebirth_req(self):
        return REBIRTH_BASE * (REBIRTH_REQ_GROWTH ** min(self.rebirths, 200)) * \
            ((1 - SP_REQ_STEP) ** self.slvl("sp_req"))

    def pr_gain(self):
        req = self.rebirth_req()
        if self.run_points < req:
            return 0
        g = (1 + self.rebirths) * ((self.run_points / req) ** PR_EXPONENT) * (PR_FORTUNE ** self.lvl("pr_fortune"))
        return float(max(1, int(min(g, MAX_NUM))))

    def start_capital(self):
        l = self.lvl("pr_start")
        return PR_START_BASE * (PR_START_MULT ** (l - 1)) if l > 0 else 0.0

    def do_rebirth(self):
        gain = self.pr_gain()
        if gain <= 0:
            return 0
        self.pr = min(self.pr + gain, MAX_NUM)
        self.rebirths += 1
        self.total_rebirths += 1
        self.reset_run(self.start_capital())
        self.recalc()
        return gain

    def pr_cost(self, uid):
        d = PR_DEF[uid]
        return float(math.ceil(d[3] * (d[4] ** self.lvl(uid))))

    def pr_maxed(self, uid):
        d = PR_DEF[uid]
        return d[5] > 0 and self.lvl(uid) >= d[5]

    def buy_pr(self, uid):
        if self.pr_maxed(uid):
            return False
        c = self.pr_cost(uid)
        if self.pr < c:
            return False
        self.pr -= c
        self.pr_ups[uid] = self.lvl(uid) + 1
        self.recalc()
        return True

    # ---------- super renacimiento ----------
    def super_min(self):
        return SUPER_MIN_REBIRTHS + SUPER_MIN_STEP * self.supers

    def can_super(self):
        return self.rebirths >= self.super_min()

    def super_sp_gain(self):
        return float(max(1, self.rebirths // SUPER_SP_DIV))

    def super_start_pr(self):
        base = SUPER_START_PR * (SUPER_START_GROWTH ** min(self.supers, 100))
        return float(int(base * (1 + SP_PR_STEP * self.slvl("sp_pr"))))

    def do_super(self):
        if not self.can_super():
            return (0, 0)
        gain = self.super_sp_gain()
        start = self.super_start_pr()
        self.sp += gain
        self.supers += 1
        self.rebirths = 0
        self.pr = start
        self.pr_ups = {}
        self.reset_run(0.0)
        self.recalc()
        return (gain, start)

    def sp_cost(self, uid):
        d = SP_DEF[uid]
        return float(math.ceil(d[3] * (d[4] ** self.slvl(uid))))

    def sp_maxed(self, uid):
        d = SP_DEF[uid]
        return d[5] > 0 and self.slvl(uid) >= d[5]

    def buy_sp(self, uid):
        if self.sp_maxed(uid):
            return False
        c = self.sp_cost(uid)
        if self.sp < c:
            return False
        self.sp -= c
        self.sp_ups[uid] = self.slvl(uid) + 1
        self.recalc()
        return True

    # ---------- efectos (texto) ----------
    def effect(self, uid):
        l = self.lvl(uid)
        if uid == "pr_power":
            return "Actual: x%s Puntos" % fmt(PR_POWER ** l)
        if uid == "pr_fortune":
            return "Actual: x%s PR" % fmt(PR_FORTUNE ** l)
        if uid == "pr_click":
            return "Actual: x%s clic" % fmt(PR_CLICK ** l)
        if uid == "pr_start":
            return "Actual: %s Puntos al renacer" % fmt(self.start_capital())
        if uid == "pr_discount":
            return "Actual: -%d%% coste" % round((1 - (1 - PR_DISCOUNT_STEP) ** l) * 100)
        if uid == "pr_autoclick":
            return "Actual: %s clics/s" % fmt(l * AUTOCLICK_PER)
        if uid == "pr_autobuy":
            return "Actual: " + ("Desbloqueado" if l else "Bloqueado")
        if uid == "pr_milestone":
            return "Actual: hitos x%s" % fmt(MILESTONE_MULT + MILESTONE_STEP * l)
        if uid == "pr_offline":
            return "Actual: %d%% offline" % round(self.off_eff() * 100)
        if uid == "pr_synergy":
            return "Actual: +%d%% de Puntos/s por clic" % round(SYN_STEP * l * 100)
        return ""

    def seffect(self, uid):
        l = self.slvl(uid)
        if uid == "sp_mult":
            return "Actual: x%s Puntos" % fmt(SP_MULT_PER ** l)
        if uid == "sp_pr":
            return "Actual: +%d%% PR iniciales" % round(SP_PR_STEP * l * 100)
        if uid == "sp_req":
            return "Actual: -%d%% requisito" % round((1 - (1 - SP_REQ_STEP) ** l) * 100)
        if uid == "sp_discount":
            return "Actual: -%d%% coste" % round((1 - (1 - SP_DISC_STEP) ** l) * 100)
        if uid == "sp_autorebirth":
            return "Actual: " + ("Desbloqueado" if l else "Bloqueado")
        return ""

    # ---------- offline ----------
    def off_eff(self):
        return min(1.0, OFFLINE_BASE_EFF + OFFLINE_STEP * self.lvl("pr_offline"))

    def apply_offline(self, elapsed):
        if elapsed < 30:
            return 0.0
        self.recalc()
        gain = self.pps * min(elapsed, OFFLINE_MAX_HOURS * 3600) * self.off_eff()
        if gain > 0:
            self.add_points(gain)
        return gain

    # ---------- ticks ----------
    def tick(self, dt):
        self.recalc()
        self.play_time += dt
        gain = self.pps * dt
        acps = self.lvl("pr_autoclick") * AUTOCLICK_PER
        if acps:
            gain += self.click_val * acps * dt
        if gain > 0:
            self.add_points(gain)
        self._t_auto += dt
        if self._t_auto >= 0.5:
            self._t_auto = 0.0
            self.auto_actions()
        self._t_ach += dt
        if self._t_ach >= 1.0:
            self._t_ach = 0.0
            self.check_ach()

    def auto_actions(self):
        if self.auto_buy and self.lvl("pr_autobuy") > 0:
            for _ in range(8):
                best, br = None, None
                for i in range(len(GENS)):
                    c = self.gen_cost(i, 1)
                    if c <= self.points * AUTOBUY_BUDGET:
                        r = c / GENS[i][2]
                        if best is None or r < br:
                            best, br = i, r
                if best is None:
                    break
                self.buy_gen(best, 1)
        if self.auto_rebirth and self.slvl("sp_autorebirth") > 0:
            if self.pr_gain() > 0 and self.run_points >= self.rebirth_req() * AUTO_REBIRTH_FACTOR:
                g = self.do_rebirth()
                self.msgs.append("Auto-Renacimiento: +%s PR" % fmt(g))

    def check_ach(self):
        for aid, name, desc, fn in ACHS:
            if aid not in self.ach and fn(self):
                self.ach.add(aid)
                self.msgs.append("Logro desbloqueado: %s" % name)

    # ---------- guardado ----------
    def save(self, path):
        d = dict(points=self.points, run_points=self.run_points, lifetime=self.lifetime, clicks=self.clicks,
                 owned=self.owned, ups=sorted(self.ups), rebirths=self.rebirths,
                 total_rebirths=self.total_rebirths, pr=self.pr, pr_ups=self.pr_ups, supers=self.supers,
                 sp=self.sp, sp_ups=self.sp_ups, ach=sorted(self.ach), auto_buy=self.auto_buy,
                 auto_rebirth=self.auto_rebirth, play_time=self.play_time, saved_at=time.time())
        try:
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(d, f)
            os.replace(tmp, path)
        except Exception:
            pass

    def load(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            return 0.0
        try:
            self.points = float(d.get("points", 0))
            self.run_points = float(d.get("run_points", 0))
            self.lifetime = float(d.get("lifetime", 0))
            self.clicks = int(d.get("clicks", 0))
            ow = d.get("owned", [])
            self.owned = [int(ow[i]) if i < len(ow) else 0 for i in range(len(GENS))]
            self.ups = set(d.get("ups", []))
            self.rebirths = int(d.get("rebirths", 0))
            self.total_rebirths = int(d.get("total_rebirths", self.rebirths))
            self.pr = float(d.get("pr", 0))
            self.pr_ups = dict((k, int(v)) for k, v in d.get("pr_ups", {}).items() if k in PR_DEF)
            self.supers = int(d.get("supers", 0))
            self.sp = float(d.get("sp", 0))
            self.sp_ups = dict((k, int(v)) for k, v in d.get("sp_ups", {}).items() if k in SP_DEF)
            self.ach = set(d.get("ach", []))
            self.auto_buy = bool(d.get("auto_buy", False))
            self.auto_rebirth = bool(d.get("auto_rebirth", False))
            self.play_time = float(d.get("play_time", 0))
            saved_at = float(d.get("saved_at", time.time()))
        except Exception:
            self.reset_all()
            return 0.0
        self.recalc()
        return self.apply_offline(time.time() - saved_at)


# ===== UI =====
# =====================================================================
# INTERFAZ
# =====================================================================
def make_btn(text, color=ACCENT, fs=13, size_hint=(1, 1), **kw):
    return Button(text=text, markup=True, halign="center", valign="middle", background_normal="",
                  background_down="", background_color=color, font_size=sp(fs), size_hint=size_hint, **kw)


def make_scroll():
    sv = ScrollView(do_scroll_x=False, bar_width=dp(3))
    grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(6), padding=dp(6))
    grid.bind(minimum_height=grid.setter("height"))
    sv.add_widget(grid)
    return sv, grid


class InfoLabel(Label):
    def __init__(self, h, **kw):
        super().__init__(markup=True, size_hint_y=None, height=dp(h), halign="left", valign="top",
                         font_size=sp(13), **kw)
        self.bind(size=lambda w, s: setattr(w, "text_size", (s[0] - dp(12), s[1])))


class Row(BoxLayout):
    def __init__(self, on_press=None, height=84, **kw):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(height), spacing=dp(6),
                         padding=(dp(8), dp(5)), **kw)
        with self.canvas.before:
            Color(*PANEL)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._sync, size=self._sync)
        self.info = Label(markup=True, halign="left", valign="middle", font_size=sp(13),
                          size_hint_x=0.64 if on_press else 1)
        self.info.bind(size=lambda w, s: setattr(w, "text_size", s))
        self.add_widget(self.info)
        self.btn = None
        if on_press:
            self.btn = make_btn("", ACCENT, size_hint=(0.36, 1))
            self.btn.bind(on_release=lambda *_: on_press())
            self.add_widget(self.btn)

    def _sync(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def set(self, info, btn=None, color=None):
        if self.info.text != info:
            self.info.text = info
        if self.btn is not None:
            if btn is not None and self.btn.text != btn:
                self.btn.text = btn
            if color is not None:
                self.btn.background_color = color


class Toast(Label):
    def __init__(self, text, **kw):
        super().__init__(text=text, size_hint=(0.92, None), height=dp(42), font_size=sp(13),
                         pos_hint={"center_x": 0.5, "top": 0.985}, **kw)
        with self.canvas.before:
            Color(0.1, 0.13, 0.25, 0.96)
            self._r = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._s, size=self._s)

    def _s(self, *a):
        self._r.pos = self.pos
        self._r.size = self.size


class ClickButton(Button):
    def __init__(self, cb, **kw):
        super().__init__(**kw)
        self.cb = cb

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.cb(touch.pos)
        return super().on_touch_down(touch)


# ---------------------------------------------------------------- pestanas
class GensTab(BoxLayout):
    def __init__(self, app):
        super().__init__(orientation="vertical")
        self.app = app
        bar = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(4), padding=(dp(6), dp(3)))
        self.mode_btns = []
        for label, val in (("x1", 1), ("x10", 10), ("x100", 100), ("MAX", 0)):
            b = make_btn(label, PANEL2)
            b.bind(on_release=lambda w, v=val: app.set_mode(v))
            bar.add_widget(b)
            self.mode_btns.append((val, b))
        self.auto_btn = make_btn("Auto", PANEL2, fs=12)
        self.auto_btn.bind(on_release=lambda *_: app.toggle_auto_buy())
        bar.add_widget(self.auto_btn)
        self.add_widget(bar)
        sv, grid = make_scroll()
        self.rows = []
        for i in range(len(GENS)):
            r = Row(on_press=lambda i=i: app.buy_gen(i), height=88)
            grid.add_widget(r)
            self.rows.append(r)
        self.add_widget(sv)

    def refresh(self):
        app = self.app
        g = app.game
        for val, b in self.mode_btns:
            b.background_color = ACCENT if app.buy_mode == val else PANEL2
        if g.lvl("pr_autobuy") > 0:
            self.auto_btn.text = "Auto: " + ("ON" if g.auto_buy else "OFF")
            self.auto_btn.background_color = GREEN if g.auto_buy else PANEL2
        else:
            self.auto_btn.text = "Auto: bloq."
            self.auto_btn.background_color = DISABLED
        for i, r in enumerate(self.rows):
            n = app.buy_mode if app.buy_mode > 0 else max(1, g.max_buy(i))
            cost = g.gen_cost(i, n)
            unit = g.unit_rate(i)
            nm = g.next_milestone(i)
            if nm:
                hito = "Hito x%s en %d" % (fmt(g.milestone_mult()), nm)
            else:
                hito = "Hitos completados"
            info = ("[b]%s[/b]  [color=ffd54a]x%d[/color]\n"
                    "[size=11sp]%s/s c/u  |  Total %s/s[/size]\n"
                    "[size=11sp][color=9fd3ff]%s[/color][/size]") % (
                GENS[i][0], g.owned[i], fmt(unit), fmt(unit * g.owned[i]), hito)
            r.set(info, "Comprar %d\n%s" % (n, fmt(cost)), GREEN if g.points >= cost else DISABLED)


class UpsTab(BoxLayout):
    def __init__(self, app):
        super().__init__(orientation="vertical")
        self.app = app
        self.add_widget(Label(text="[b]Mejoras de Puntos[/b]  (se reinician al Renacer)", markup=True,
                              size_hint_y=None, height=dp(30), font_size=sp(13)))
        sv, self.grid = make_scroll()
        self.add_widget(sv)
        self.cur_ids = None
        self.rows = []
        self.empty = InfoLabel(70)
        self.empty.text = "No hay mejoras disponibles ahora.\nCompra mas generadores para desbloquear nuevas."

    def refresh(self):
        g = self.app.game
        av = g.available_upgrades()
        ids = [u[0] for u in av]
        if ids != self.cur_ids:
            self.cur_ids = ids
            self.grid.clear_widgets()
            self.rows = []
            if not av:
                self.grid.add_widget(self.empty)
            for u in av:
                r = Row(on_press=lambda uid=u[0]: self.app.buy_up(uid), height=80)
                self.grid.add_widget(r)
                self.rows.append(r)
        for r, u in zip(self.rows, av):
            r.set("[b]%s[/b]\n[size=11sp]%s[/size]" % (u[1], u[2]), "Comprar\n%s" % fmt(u[3]),
                  GREEN if g.points >= u[3] else DISABLED)


class RebirthTab(BoxLayout):
    def __init__(self, app):
        super().__init__(orientation="vertical")
        self.app = app
        sv, grid = make_scroll()
        self.info = InfoLabel(150)
        grid.add_widget(self.info)
        self.btn = make_btn("", GREEN, size_hint=(1, None), height=dp(66))
        self.btn.bind(on_release=lambda *_: app.do_rebirth())
        grid.add_widget(self.btn)
        self.rows = {}
        for u in PR_UPS:
            r = Row(on_press=lambda uid=u[0]: app.buy_pr(uid), height=92)
            grid.add_widget(r)
            self.rows[u[0]] = r
        self.add_widget(sv)

    def refresh(self):
        app = self.app
        g = app.game
        gain = g.pr_gain()
        self.info.text = (
            "[b]RENACIMIENTO[/b]\n"
            "Renacimientos: [b]%d[/b]  (Puntos x%s)\n"
            "Puntos de Renacimiento: [color=ffd54a][b]%s PR[/b][/color]\n"
            "Requisito: %s Puntos en la ronda (llevas %s)\n"
            "Reinicia: Puntos, generadores y mejoras normales.\n"
            "Cada renacimiento: Puntos x%s permanente."
        ) % (g.rebirths, fmt(REBIRTH_MULT ** min(g.rebirths, 900)), fmt(g.pr), fmt(g.rebirth_req()),
             fmt(g.run_points), fmt(REBIRTH_MULT))
        if app.is_pending("reb"):
            self.btn.text = "[b]Seguro? Pulsa otra vez[/b]\n+%s PR" % fmt(gain)
            self.btn.background_color = ORANGE
        elif gain > 0:
            self.btn.text = "[b]RENACER[/b]\n+%s PR" % fmt(gain)
            self.btn.background_color = GREEN
        else:
            self.btn.text = "[b]Aun no puedes renacer[/b]\nNecesitas %s Puntos" % fmt(g.rebirth_req())
            self.btn.background_color = DISABLED
        for u in PR_UPS:
            uid = u[0]
            l = g.lvl(uid)
            mx = "/%d" % u[5] if u[5] else ""
            info = "[b]%s[/b]  Nv %d%s\n[size=11sp]%s[/size]\n[size=11sp][color=9fd3ff]%s[/color][/size]" % (
                u[1], l, mx, u[2], g.effect(uid))
            if g.pr_maxed(uid):
                self.rows[uid].set(info, "MAX", DISABLED)
            else:
                c = g.pr_cost(uid)
                self.rows[uid].set(info, "Mejorar\n%s PR" % fmt(c), GREEN if g.pr >= c else DISABLED)


class SuperTab(BoxLayout):
    def __init__(self, app):
        super().__init__(orientation="vertical")
        self.app = app
        sv, grid = make_scroll()
        self.info = InfoLabel(190)
        grid.add_widget(self.info)
        self.btn = make_btn("", PURPLE, size_hint=(1, None), height=dp(66))
        self.btn.bind(on_release=lambda *_: app.do_super())
        grid.add_widget(self.btn)
        self.auto_btn = make_btn("", PANEL2, size_hint=(1, None), height=dp(44), fs=12)
        self.auto_btn.bind(on_release=lambda *_: app.toggle_auto_rebirth())
        grid.add_widget(self.auto_btn)
        self.rows = {}
        for u in SP_UPS:
            r = Row(on_press=lambda uid=u[0]: app.buy_sp(uid), height=92)
            grid.add_widget(r)
            self.rows[u[0]] = r
        self.add_widget(sv)

    def refresh(self):
        app = self.app
        g = app.game
        self.info.text = (
            "[b]SUPER RENACIMIENTO[/b]\n"
            "Super Renacimientos: [b]%d[/b]  (Puntos x%s permanente)\n"
            "Super Puntos: [color=d9a6ff][b]%s SP[/b][/color]\n"
            "Requisito: %d Renacimientos (tienes %d)\n"
            "Recompensa: +%s SP y empiezas con [b]%s PR[/b]\n"
            "[color=ff8888]Reinicia TODO: Puntos, generadores, mejoras normales, Renacimientos, PR y "
            "mejoras de Renacimiento.[/color]\n"
            "Las mejoras de SP son permanentes."
        ) % (g.supers, fmt(SUPER_MULT ** min(g.supers, 150)), fmt(g.sp), g.super_min(), g.rebirths,
             fmt(g.super_sp_gain()), fmt(g.super_start_pr()))
        if app.is_pending("sup"):
            self.btn.text = "[b]Seguro? Se reinicia casi todo[/b]\nPulsa otra vez"
            self.btn.background_color = ORANGE
        elif g.can_super():
            self.btn.text = "[b]SUPER RENACER[/b]\n+%s SP  |  %s PR iniciales" % (
                fmt(g.super_sp_gain()), fmt(g.super_start_pr()))
            self.btn.background_color = PURPLE
        else:
            self.btn.text = "[b]Bloqueado[/b]\nNecesitas %d Renacimientos" % g.super_min()
            self.btn.background_color = DISABLED
        if g.slvl("sp_autorebirth") > 0:
            self.auto_btn.text = "Auto-Renacer: " + ("ON" if g.auto_rebirth else "OFF")
            self.auto_btn.background_color = GREEN if g.auto_rebirth else PANEL2
        else:
            self.auto_btn.text = "Auto-Renacer: bloqueado"
            self.auto_btn.background_color = DISABLED
        for u in SP_UPS:
            uid = u[0]
            l = g.slvl(uid)
            mx = "/%d" % u[5] if u[5] else ""
            info = "[b]%s[/b]  Nv %d%s\n[size=11sp]%s[/size]\n[size=11sp][color=d9a6ff]%s[/color][/size]" % (
                u[1], l, mx, u[2], g.seffect(uid))
            if g.sp_maxed(uid):
                self.rows[uid].set(info, "MAX", DISABLED)
            else:
                c = g.sp_cost(uid)
                self.rows[uid].set(info, "Mejorar\n%s SP" % fmt(c), PURPLE if g.sp >= c else DISABLED)


class AchTab(BoxLayout):
    def __init__(self, app):
        super().__init__(orientation="vertical")
        self.app = app
        sv, grid = make_scroll()
        self.stats = InfoLabel(190)
        grid.add_widget(self.stats)
        self.rows = []
        for _ in ACHS:
            r = Row(height=60)
            grid.add_widget(r)
            self.rows.append(r)
        self.reset_btn = make_btn("", RED, size_hint=(1, None), height=dp(52), fs=12)
        self.reset_btn.bind(on_release=lambda *_: app.do_reset())
        grid.add_widget(self.reset_btn)
        self.add_widget(sv)

    def refresh(self):
        app = self.app
        g = app.game
        self.stats.text = (
            "[b]ESTADISTICAS[/b]\n"
            "Puntos totales: %s\nClics: %s\nTiempo jugado: %s\n"
            "Renacimientos totales: %d\nSuper Renacimientos: %d\n"
            "Logros: %d/%d  (bonus x%s a los Puntos)"
        ) % (fmt(g.lifetime), fmt(g.clicks), fmt_time(g.play_time), g.total_rebirths, g.supers,
             len(g.ach), len(ACHS), fmt(ACH_BONUS ** len(g.ach)))
        for r, a in zip(self.rows, ACHS):
            if a[0] in g.ach:
                r.set("[color=66ff88][b]%s[/b][/color]\n[size=11sp]%s[/size]" % (a[1], a[2]))
            else:
                r.set("[color=888888][b]%s[/b]\n[size=11sp]%s[/size][/color]" % (a[1], a[2]))
        if app.is_pending("reset"):
            self.reset_btn.text = "Seguro? Se borra TODO. Pulsa otra vez"
        else:
            self.reset_btn.text = "Reiniciar todo el progreso"


# ---------------------------------------------------------------- app
class ClickerApp(App):
    title = APP_TITLE

    def build(self):
        Window.clearcolor = BG
        if platform not in ("android", "ios"):
            Window.size = DEV_WINDOW
        self.game = Game()
        self.save_path = os.path.join(self.user_data_dir, SAVE_FILE)
        offline = self.game.load(self.save_path)
        self.buy_mode = 1
        self.pending = {}
        self.pop_n = 0
        self.toast_queue = []
        self.toast_busy = False
        self.paused_at = None
        self.tab_idx = 0

        root = FloatLayout()
        main = BoxLayout(orientation="vertical", size_hint=(1, 1), padding=dp(4), spacing=dp(4))

        header = BoxLayout(orientation="vertical", size_hint_y=0.13)
        self.lbl_points = Label(markup=True, font_size=sp(30), size_hint_y=0.52)
        self.lbl_pps = Label(markup=True, font_size=sp(15), color=(0.6, 0.85, 1, 1), size_hint_y=0.24)
        self.lbl_info = Label(markup=True, font_size=sp(12), color=(0.75, 0.75, 0.85, 1), size_hint_y=0.24)
        for w in (self.lbl_points, self.lbl_pps, self.lbl_info):
            header.add_widget(w)
        main.add_widget(header)

        zone = FloatLayout(size_hint_y=0.20)
        self.click_btn = ClickButton(self.on_click, text="", markup=True, halign="center", valign="middle",
                                     background_normal="", background_down="", background_color=ACCENT,
                                     font_size=sp(22), size_hint=(0.94, 0.94), pos_hint={"center_x": .5, "center_y": .5})
        self.click_btn.bind(state=lambda w, s: setattr(w, "background_color",
                                                       (0.15, 0.40, 0.80, 1) if s == "down" else ACCENT))
        zone.add_widget(self.click_btn)
        main.add_widget(zone)

        self.content = BoxLayout(size_hint_y=0.59)
        main.add_widget(self.content)

        self.tabs = [GensTab(self), UpsTab(self), RebirthTab(self), SuperTab(self), AchTab(self)]
        bar = BoxLayout(size_hint_y=0.08, spacing=dp(3))
        self.tab_btns = []
        for i, name in enumerate(("Compras", "Mejoras", "Renacer", "Super", "Logros")):
            b = make_btn(name, PANEL2, fs=12)
            b.bind(on_release=lambda w, i=i: self.show_tab(i))
            bar.add_widget(b)
            self.tab_btns.append(b)
        main.add_widget(bar)

        root.add_widget(main)
        self.overlay = FloatLayout(size_hint=(1, 1))
        root.add_widget(self.overlay)

        self.show_tab(0)
        Clock.schedule_interval(self.logic_tick, LOGIC_TICK)
        Clock.schedule_interval(self.ui_tick, UI_TICK)
        Clock.schedule_interval(self.autosave, AUTOSAVE_SECS)
        if offline > 0:
            self.toast("Bienvenido de nuevo: +%s Puntos offline" % fmt(offline))
        return root

    # ----- ciclo de vida
    def on_pause(self):
        self.game.save(self.save_path)
        self.paused_at = time.time()
        return True

    def on_resume(self):
        if self.paused_at:
            gain = self.game.apply_offline(time.time() - self.paused_at)
            if gain > 0:
                self.toast("Bienvenido de nuevo: +%s Puntos offline" % fmt(gain))
        self.paused_at = None

    def on_stop(self):
        self.game.save(self.save_path)

    # ----- ticks
    def logic_tick(self, dt):
        self.game.tick(min(dt, 1.0))
        if self.game.msgs:
            for m in self.game.msgs:
                self.toast(m)
            self.game.msgs = []

    def ui_tick(self, dt):
        self.refresh_ui()

    def autosave(self, dt):
        self.game.save(self.save_path)

    def refresh_ui(self):
        g = self.game
        self.lbl_points.text = "[b]%s[/b] Puntos" % fmt(g.points)
        self.lbl_pps.text = "%s Puntos/s" % fmt(g.pps)
        self.lbl_info.text = "Mult. global x%s  |  Renac. %d  |  Super %d  |  PR %s" % (
            fmt(g.gmult), g.rebirths, g.supers, fmt(g.pr))
        self.click_btn.text = "[b]CLIC[/b]\n[size=14sp]+%s Puntos[/size]" % fmt(g.click_val)
        self.tabs[self.tab_idx].refresh()

    def show_tab(self, i):
        self.tab_idx = i
        self.content.clear_widgets()
        self.content.add_widget(self.tabs[i])
        for j, b in enumerate(self.tab_btns):
            b.background_color = ACCENT if j == i else PANEL2
        self.refresh_ui()

    # ----- acciones
    def on_click(self, pos):
        v = self.game.click()
        self.popup(pos, "+" + fmt(v))
        self.lbl_points.text = "[b]%s[/b] Puntos" % fmt(self.game.points)

    def set_mode(self, v):
        self.buy_mode = v
        self.refresh_ui()

    def buy_gen(self, i):
        self.game.buy_gen(i, self.buy_mode)
        self.refresh_ui()

    def buy_up(self, uid):
        self.game.buy_up(uid)
        self.refresh_ui()

    def buy_pr(self, uid):
        self.game.buy_pr(uid)
        self.refresh_ui()

    def buy_sp(self, uid):
        self.game.buy_sp(uid)
        self.refresh_ui()

    def toggle_auto_buy(self):
        if self.game.lvl("pr_autobuy") > 0:
            self.game.auto_buy = not self.game.auto_buy
        else:
            self.toast("Desbloquea el Auto-Comprador con PR")
        self.refresh_ui()

    def toggle_auto_rebirth(self):
        if self.game.slvl("sp_autorebirth") > 0:
            self.game.auto_rebirth = not self.game.auto_rebirth
        else:
            self.toast("Desbloquea el Auto-Renacimiento con SP")
        self.refresh_ui()

    def confirm(self, key):
        now = time.time()
        if self.pending.get(key, 0) > now:
            self.pending[key] = 0
            return True
        self.pending[key] = now + 3.0
        return False

    def is_pending(self, key):
        return self.pending.get(key, 0) > time.time()

    def do_rebirth(self):
        g = self.game
        if g.pr_gain() <= 0:
            self.toast("Aun no cumples el requisito de Renacimiento")
        elif self.confirm("reb"):
            gain = g.do_rebirth()
            self.toast("Renaciste! +%s PR" % fmt(gain))
            g.save(self.save_path)
        self.refresh_ui()

    def do_super(self):
        g = self.game
        if not g.can_super():
            self.toast("Necesitas %d Renacimientos" % g.super_min())
        elif self.confirm("sup"):
            sp_gain, start = g.do_super()
            self.toast("SUPER RENACIMIENTO! +%s SP, %s PR iniciales" % (fmt(sp_gain), fmt(start)))
            g.save(self.save_path)
        self.refresh_ui()

    def do_reset(self):
        if self.confirm("reset"):
            self.game.reset_all()
            self.game.save(self.save_path)
            self.toast("Progreso reiniciado")
        self.refresh_ui()

    # ----- efectos visuales
    def popup(self, pos, text):
        if self.pop_n >= 14:
            return
        lbl = Label(text=text, size_hint=(None, None), size=(dp(150), dp(30)), font_size=sp(18), bold=True,
                    color=GOLD, pos=(pos[0] - dp(75), pos[1]))
        self.overlay.add_widget(lbl)
        self.pop_n += 1
        anim = Animation(y=pos[1] + dp(80), opacity=0, duration=0.7)

        def done(*a):
            self.overlay.remove_widget(lbl)
            self.pop_n -= 1
        anim.bind(on_complete=done)
        anim.start(lbl)

    def toast(self, text):
        self.toast_queue.append(text)
        if not self.toast_busy:
            self._next_toast()

    def _next_toast(self):
        if not self.toast_queue:
            self.toast_busy = False
            return
        self.toast_busy = True
        t = Toast(self.toast_queue.pop(0))
        self.overlay.add_widget(t)
        fast = len(self.toast_queue) > 2
        anim = Animation(opacity=1, duration=0.6 if fast else 1.8) + Animation(opacity=0, duration=0.4)

        def done(*a):
            self.overlay.remove_widget(t)
            self._next_toast()
        anim.bind(on_complete=done)
        anim.start(t)


if __name__ == "__main__":
    ClickerApp().run()
