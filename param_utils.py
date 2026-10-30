# -*- coding: utf-8 -*-
"""
param_utils.py —— 随机数生成器的「参数处理核心」

本模块集中处理所有与参数有关的脏活：
    * 输入清洗（全角/半角、空格、千分位逗号、不可见字符）
    * 非法输入的自动纠正（小数取整、越界钳制、最小值/最大值互换）
    * 无法自动纠正时给出面向用户的、带解决方案的友好报错
    * 校验通过后真正生成随机数

设计原则：UI 层只负责收集字符串，所有判断都在这里完成。
         这样无论从窗口、命令行还是单元测试调用，行为都完全一致。
"""

from __future__ import annotations

import math
import random
import unicodedata
from dataclasses import dataclass

# --------------------------------------------------------------------------
# 常量（需求规定的硬性边界）
# --------------------------------------------------------------------------
VALUE_LIMIT = 10_000        # 取值范围：-10000 ~ +10000
COUNT_MIN = 1               # 每次生成个数下限
COUNT_MAX = 50              # 每次生成个数上限

DEFAULT_MIN = 0
DEFAULT_MAX = 100
DEFAULT_COUNT = 5
DEFAULT_DUPLICATE = True


# --------------------------------------------------------------------------
# 异常
# --------------------------------------------------------------------------
class ParamError(Exception):
    """参数存在无法自动纠正的问题。

    message 面向最终用户：先说明「哪里错了」，再给出「怎么改」。
    field 用于让 UI 把焦点定位到出错的输入框。
    """

    def __init__(self, title: str, message: str, field: str = ""):
        super().__init__(message)
        self.title = title
        self.message = message
        self.field = field


# --------------------------------------------------------------------------
# 参数对象
# --------------------------------------------------------------------------
@dataclass
class Params:
    min_value: int = DEFAULT_MIN
    max_value: int = DEFAULT_MAX
    count: int = DEFAULT_COUNT
    allow_duplicate: bool = DEFAULT_DUPLICATE

    def describe(self) -> str:
        dup = "允许重复" if self.allow_duplicate else "不允许重复"
        return f"范围 [{self.min_value}, {self.max_value}]　个数 {self.count}　{dup}"

    def copy(self) -> "Params":
        return Params(self.min_value, self.max_value,
                      self.count, self.allow_duplicate)


# --------------------------------------------------------------------------
# 内部工具
# --------------------------------------------------------------------------
def _clean(raw) -> str:
    """把用户输入洗成「可以直接喂给 int()」的样子。"""
    if raw is None:
        return ""
    text = unicodedata.normalize("NFKC", str(raw))   # 全角数字/符号 → 半角
    text = text.strip()
    # 去掉肉眼看不见、但会害死 int() 的字符
    for ch in (" ", "\t", "\r", "\n", "_", ",", "，", "、"):
        text = text.replace(ch, "")
    return text


# --------------------------------------------------------------------------
# 单个整数参数解析
# --------------------------------------------------------------------------
def parse_int_field(raw, field_name: str, low: int, high: int, default: int):
    """解析并自动纠正一个整数参数。

    返回 (value, corrections)
        corrections 是给用户看的「我帮你改了什么」说明列表。

    无法解析时抛出 ParamError（带指正方案）。
    """
    corrections: list[str] = []
    text = _clean(raw)

    # ---- 1. 空输入：用默认值兜底 ----
    if text == "":
        corrections.append(f"「{field_name}」为空，已自动填入默认值 {default}")
        return default, corrections

    # ---- 2. 只有符号的输入：没法猜意图，直接报错 ----
    if text in {"+", "-", ".", "+.", "-."}:
        raise ParamError(
            "参数无法识别",
            f"「{field_name}」的输入「{raw}」不是一个完整的数字。\n\n"
            f"【请这样修改】\n"
            f"· 输入一个整数，例如 0、-50、100\n"
            f"· 该参数的合法范围是 {low} ~ {high}",
            field_name,
        )

    # ---- 3. 先当整数解析，失败再当小数解析 ----
    try:
        value = int(text)
    except ValueError:
        try:
            number = float(text)
        except (ValueError, TypeError):
            raise ParamError(
                "参数无法识别",
                f"「{field_name}」的输入「{raw}」里含有无法识别的字符。\n\n"
                f"【请这样修改】\n"
                f"· 只输入数字（可以带负号），例如 -50、0、100\n"
                f"· 不要输入字母、中文或其它符号\n"
                f"· 该参数的合法范围是 {low} ~ {high}",
                field_name,
            ) from None

        if not math.isfinite(number):
            raise ParamError(
                "参数无法识别",
                f"「{field_name}」的输入「{raw}」不是一个有限的数字。\n\n"
                f"【请这样修改】\n"
                f"· 输入一个普通整数，例如 0、-50、100\n"
                f"· 该参数的合法范围是 {low} ~ {high}",
                field_name,
            )

        value = int(number)          # 向零截断，即「取整数位」
        if number != value:
            corrections.append(
                f"「{field_name}」输入的是小数 {text}，已自动取整数位为 {value}"
            )

    # ---- 4. 超范围钳制 ----
    if value < low:
        corrections.append(
            f"「{field_name}」的值 {value} 小于下限，已自动调整为 {low}"
        )
        value = low
    elif value > high:
        corrections.append(
            f"「{field_name}」的值 {value} 大于上限，已自动调整为 {high}"
        )
        value = high

    return value, corrections


# --------------------------------------------------------------------------
# 可行性校验（能否真的生成出来）
# --------------------------------------------------------------------------
def check_feasible(params: Params) -> None:
    """检查这组参数是否真的能生成出结果。不满足时抛出带解决方案的 ParamError。"""
    span = params.max_value - params.min_value + 1
    if params.allow_duplicate:
        return
    if params.count > span:
        raise ParamError(
            "这组参数无法生成",
            f"当前范围 [{params.min_value}, {params.max_value}] 里只有 {span} 个不同的整数，\n"
            f"但每次要生成 {params.count} 个且「不允许重复」，因此无法完成。\n\n"
            f"【请任选一种改法】\n"
            f"1. 扩大取值范围：让它至少包含 {params.count} 个整数\n"
            f"2. 勾选「允许重复生成」\n"
            f"3. 把「每次生成的个数」改成 {span} 或更小",
            "生成个数 / 允许重复",
        )


# --------------------------------------------------------------------------
# 总入口：把界面字符串 → 可靠 Params
# --------------------------------------------------------------------------
def build_params(raw_min, raw_max, raw_count, allow_duplicate):
    """把界面上的三个字符串 + 一个开关，变成可靠的 Params。

    返回 (params, corrections)；无法自动纠正时抛 ParamError。
    """
    corrections: list[str] = []

    lo, c = parse_int_field(raw_min, "最小值", -VALUE_LIMIT, VALUE_LIMIT, DEFAULT_MIN)
    corrections.extend(c)
    hi, c = parse_int_field(raw_max, "最大值", -VALUE_LIMIT, VALUE_LIMIT, DEFAULT_MAX)
    corrections.extend(c)
    cnt, c = parse_int_field(raw_count, "每次生成个数", COUNT_MIN, COUNT_MAX, DEFAULT_COUNT)
    corrections.extend(c)

    # 最小值 > 最大值：自动交换
    if lo > hi:
        corrections.append(f"最小值 {lo} 大于最大值 {hi}，已自动交换为 [{hi}, {lo}]")
        lo, hi = hi, lo

    params = Params(lo, hi, cnt, bool(allow_duplicate))
    check_feasible(params)
    return params, corrections


# --------------------------------------------------------------------------
# 生成
# --------------------------------------------------------------------------
def generate_numbers(params: Params) -> list[int]:
    """按参数生成随机数列表。"""
    check_feasible(params)      # 防止有人绕过 build_params 直接调用
    lo, hi, n = params.min_value, params.max_value, params.count

    if params.allow_duplicate:
        return [random.randint(lo, hi) for _ in range(n)]

    # 用 range 作为总体，即使区间很大也不会真的展开成列表，内存安全
    return random.sample(range(lo, hi + 1), n)


# --------------------------------------------------------------------------
# 自测：python param_utils.py
# --------------------------------------------------------------------------
if __name__ == "__main__":
    cases = [
        ("-50", "100", "5", True),        # 正常
        ("  3.9 ", "12.2", "2.7", False), # 小数 + 空格
        ("100", "-100", "60", True),      # 大小值颠倒 + 越界
        ("abc", "10", "5", True),         # 非数字 → 报错
        ("0", "5", "10", False),          # 不可能任务 → 报错
        ("", "", "", True),               # 全空 → 默认值
        ("1,000", "２000", "-3", True),   # 千分位 + 全角 + 负号
    ]
    for raw in cases:
        print("输入:", raw)
        try:
            p, fixes = build_params(*raw)
            print("  结果:", p.describe())
            for f in fixes:
                print("  纠正:", f)
            print("  生成:", generate_numbers(p))
        except ParamError as e:
            print("  报错:", e.title)
            print("       ", e.message.replace("\n", "\n        "))
        print()