# -*- coding: utf-8 -*-
"""时间轴规划器：把「目标时长 + 素材实测 + 解说句数」算成一张可执行的时间轴。

为什么要有这一步：档位一换（10/15/30/60秒），拍数、每拍停留、停顿、片尾能不能放
全都要重算。手算一次一个样，还会在「成片够不够铺满」这件事上翻车。先跑规划器，
算不通就在开剪前报错，省掉整轮返工。

三条设计原则：
  1. 只用实测：所有节点时长都从 ffprobe 来，不按字数估。
  2. 算不通就拒绝：给替代方案（砍拍/去停顿/去片尾/换素材），不静默硬塞。
  3. 一份配置两用：`--emit` 直接吐 build 脚本的常量块，规划结果不靠手抄。

用法（纯标准库，没有音频文件也能粗排）：
    python plan_timeline.py --target 30 --beats 6
    python plan_timeline.py --target 15 --beats 4 --bg 音频/bg.mp3 --voice 音频/a.mp3 音频/b.mp3 音频/c.mp3 音频/d.mp3
    python plan_timeline.py --target 60 --beats 13 --chapters 2 --source 15.07
    python plan_timeline.py --target 30 --beats 6 --bg 音频/bg.mp3 --emit
    python plan_timeline.py --target 10 --beats 3 --no-intro --no-outro
    python plan_timeline.py --target 30 --beats 6 --source 15.07 --extra 温馨段:5.5:6.56

退出码：0 可行；1 不可行（stderr 给出三条调整方向）。
"""
import argparse
import math
import subprocess
import sys

FPS = 30
OPS_LEAD = 0.35      # 浮窗比背景交代旁白结束时提前出画面的秒数
VOICE_LEAD = 0.15    # 每拍旁白比该拍窗口早起的秒数
VOICE_PAD = 0.10     # 旁白结束后该拍至少保留的呼吸秒数
DWELL_HINT = 2.9     # 缺口超标时估算「砍到几拍」用的参考停留

# 档位预算。dwell=每拍停留区间，beats=拍数区间，其余是各节点推荐值（秒）。
TIERS = {
    10: dict(name="10秒", ceil=10.0, floor=9.4, dwell=(1.5, 2.8), beats=(3, 5),
             pause=0.0, intro=1.2, outro=0.0, bg=2.0, tail=0.5,
             note="片短，每拍可以长一点；停顿与片尾卡二选一，通常两个都不要"),
    15: dict(name="15秒", ceil=15.0, floor=14.4, dwell=(1.8, 2.6), beats=(3, 5),
             pause=1.5, intro=1.8, outro=0.0, bg=2.6, tail=0.6,
             note="片尾卡挤不下，用出片收尾代替；要片尾就去掉停顿"),
    30: dict(name="30秒", ceil=30.0, floor=29.4, dwell=(2.6, 3.0), beats=(5, 7),
             pause=2.5, intro=2.5, outro=2.0, bg=4.9, tail=0.9,
             note="标准档：5—7拍，片头片尾都放得下"),
    60: dict(name="60秒", ceil=60.0, floor=59.0, dwell=(2.8, 3.4), beats=(10, 14),
             pause=2.5, intro=3.0, outro=2.5, bg=7.0, tail=1.2,
             note="默认拆两章、章间1.2—1.6秒满屏过渡；单章超过8拍观众跟不住"),
}


def probe(path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        raise SystemExit(f"ffprobe 失败：{path}\n{r.stderr.strip()[-300:]}")
    return float(r.stdout.strip())


def pick_tier(target: float):
    for t in sorted(TIERS):
        if target <= t + 0.001:
            return t, TIERS[t]
    return 60, TIERS[60]


def floor2(x: float) -> float:
    return math.floor(x * 100) / 100


def plan(args) -> dict:
    """算时间轴。不可行直接 SystemExit，讲清三条改法。"""
    tier_key, T = pick_tier(args.target)
    n = args.beats
    intro_on = not args.no_intro and T["intro"] > 0
    outro_on = not args.no_outro and T["outro"] > 0
    pause = 0.0 if args.no_pause else (args.pause if args.pause is not None else T["pause"])
    chapters = args.chapters or (2 if args.target >= 55 and n >= 10 else 1)
    gap = args.chapter_gap if chapters > 1 else 0.0

    warn = []
    if not (T["beats"][0] <= n <= T["beats"][1]):
        warn.append(f"拍数{n}不在{T['name']}档建议区间{T['beats'][0]}—{T['beats'][1]}：{T['note']}")

    d_bg = probe(args.bg) if args.bg else T["bg"]
    if args.voice:
        d_voice = [probe(p) for p in args.voice]
        if len(d_voice) != n:
            raise SystemExit(f"--voice 给了{len(d_voice)}条，--beats 是{n}，两者必须相等")
    else:
        d_voice = [None] * n

    intro = T["intro"] if intro_on else 0.0
    outro = T["outro"] if outro_on else 0.0
    tail = args.tail if args.tail is not None else T["tail"]

    aim = min(args.target, T["ceil"]) - 0.1        # 编码会浮，留0.1余量
    middle = aim - intro - outro
    ops_start = round(pause + d_bg - OPS_LEAD, 3)   # 中间段内的相对时间
    if ops_start < pause + 0.8:
        raise SystemExit(
            f"背景交代只有{d_bg:.2f}s，扣掉{OPS_LEAD}s提前量后几乎没满屏画面：\n"
            "  1) 交代句加长到2秒以上\n"
            "  2) 把交代拆成两句，满屏段跟着变长\n"
            "  3) --pause 调大，让成片先自己说话"
        )

    ops_span = middle - ops_start - tail - gap * (chapters - 1)
    if ops_span <= 0:
        raise SystemExit(f"固定节点吃光时长：片头{intro}+停顿{pause}+交代{d_bg:.2f}"
                         f"+收尾{tail}+片尾{outro} > {aim:.2f}s")

    dwell = floor2(ops_span / n)
    lo, hi = T["dwell"]
    if dwell < lo:
        fit = max(int(ops_span // lo), 2)
        raise SystemExit(
            f"{T['name']}档装不下{n}拍：每拍只剩{dwell:.2f}s，低于下限{lo}s。\n"
            f"三条路选一条：\n"
            f"  1) 砍到{fit}拍以内——最省事，删最次要的步骤\n"
            f"  2) 去掉片头/停顿/片尾之一，每拍回血{(intro + pause + outro):.2f}s\n"
            f"  3) 目标放到{int(T['ceil'] + 5)}秒档，换更大预算"
        )
    if dwell > hi:
        need = min(math.ceil(ops_span / hi), T["beats"][1])
        raise SystemExit(
            f"{T['name']}档{n}拍太空：每拍{dwell:.2f}s，超过上限{hi}s，画面会拖、观众划走。\n"
            f"三条路选一条：\n"
            f"  1) 加到{need}拍（{T['name']}档上限{T['beats'][1]}拍），把流程拆细\n"
            f"  2) 延长交代或停顿，吃掉多余的{ops_span - n * hi:.2f}s\n"
            f"  3) 目标降到{T['floor'] - 1:.0f}秒左右，每拍可回落到{hi}s内"
        )

    # 拍窗口与旁白落点（中间段相对时间）
    beats, t = [], ops_start
    per_chapter = math.ceil(n / chapters)
    prev_voice_end = pause + d_bg + 0.05
    for i in range(n):
        if chapters > 1 and i and i % per_chapter == 0:
            t += gap
        vs = max(t - VOICE_LEAD, prev_voice_end)
        d = d_voice[i]
        if d is not None:
            if d > dwell + VOICE_LEAD:
                raise SystemExit(
                    f"第{i + 1}拍旁白{d:.2f}s比窗口{dwell:.2f}s还长，必然压到下一拍。\n"
                    f"  1) 这句改短到{dwell - VOICE_PAD:.2f}s以内\n"
                    f"  2) 这一拍单独加长到{d + 0.15:.2f}s（从别的拍借）\n"
                    f"  3) 删这一拍，合并进上一拍"
                )
            prev_voice_end = vs + d + VOICE_PAD
        beats.append(dict(idx=i + 1, start=round(t, 3), dur=dwell,
                          voice_start=round(vs, 3), voice=round(d, 3) if d else None))
        t += dwell
    ops_end = round(t, 3)

    total = round(intro + ops_end + tail + outro, 3)
    return dict(tier=tier_key, tier_name=T["name"], target=args.target, aim=aim,
                intro=intro, outro=outro, pause=pause, bg=round(d_bg, 3),
                ops_start=ops_start, ops_end=ops_end, dwell=dwell, tail=tail,
                chapters=chapters, gap=gap, beats=beats, total=total,
                middle_need=round(ops_end + tail, 3), source=args.source, warn=warn)


def plan_base(src, need, tail, extra):
    """底板序列：让底板总长==中间段需要的长度，且结尾落在成片最后一镜。"""
    if src is None:
        return None
    use_extra = sum(e[1] for e in extra) if extra else 0.0
    avail = src + use_extra
    if need <= src:
        return dict(kind="富余",
                    segs=[("成片", 0.0, round(need - tail, 3)),
                          ("成片尾", round(max(0.0, src - tail), 3), tail)],
                    note=f"成片{src:.2f}s比需要{need:.2f}s长：中间跳掉{src - need:.2f}s，"
                         f"最后{tail}s跳片尾（跳点选动作转换处，别在动作中间跳）")
    gap = need - src
    if gap <= avail:
        if use_extra:
            segs, left = [("成片", 0.0, src)], round(gap, 3)
            for name, d, ss in extra:
                take = min(d, left)
                segs.append((name, ss, round(take, 3)))
                left = round(left - take, 3)
                if left <= 0.01:
                    break
            return dict(kind="补位＋指定素材", segs=segs,
                        note=f"缺口{gap:.2f}s由补充素材补齐" +
                             (f"，还差{left:.2f}s" if left > 0.01 else "，正好")
                             + "，补完落在成片结尾接出片收尾")
        if gap > src * 0.5:
            return dict(kind="正序补位（补位偏长）",
                        segs=[("成片", 0.0, src),
                              ("成片尾", round(src - gap, 3), round(gap, 3))],
                        note=f"缺口{gap:.2f}s超过成片一半（{src:.2f}s），观众会看出是重播。\n"
                             f"           更好的做法：--extra 指定另一条同规格素材补位，"
                             f"或把拍数砍到{max(int((src + 0.9) / DWELL_HINT), 2)}拍")
        return dict(kind="正序补位",
                    segs=[("成片", 0.0, src),
                          ("成片尾", round(src - gap, 3), round(gap, 3))],
                    note=f"缺口{gap:.2f}s：从成片{src - gap:.2f}s处正序重播到结尾，"
                         f"正好落在最后一镜")
    return dict(kind="不足", segs=[("成片", 0.0, src)],
                note=f"缺口{gap:.2f}s，可用素材只有{avail:.2f}s——换更长的成片、加素材或砍拍")


def report(p, b) -> str:
    L = [f"档位 {p['tier_name']}  目标≤{p['target']:.1f}s  规划{p['total']:.2f}s  "
         f"拍数{len(p['beats'])}  每拍{p['dwell']:.2f}s"]
    if p["chapters"] > 1:
        L.append(f"分{p['chapters']}章，章间过渡{p['gap']:.2f}s；"
                 f"每章{math.ceil(len(p['beats']) / p['chapters'])}拍")
    L += ["", "  时间轴（绝对时间）"]
    if p["intro"]:
        L.append(f"  {'0.00':>6}—{p['intro']:<6.2f} 片头卡")
    else:
        L.append("  （无片头：第一拍自己当钩子，或把钩子大字叠在第一拍上）")
    t = p["intro"]
    if p["pause"]:
        L.append(f"  {t:6.2f}—{t + p['pause']:<6.2f} 停顿：成片满屏，无旁白无浮窗")
        t += p["pause"]
    L.append(f"  {t:6.2f}—{t + p['bg']:<6.2f} 背景交代旁白，满屏")
    L.append(f"  {p['intro'] + p['ops_start']:6.2f}—{p['intro'] + p['ops_end']:<6.2f} "
             f"浮窗{len(p['beats'])}拍（提前{OPS_LEAD}s出画面）")
    L.append(f"  {p['intro'] + p['ops_end']:6.2f}—{p['total'] - p['outro']:<6.2f} 出片收尾，满屏")
    if p["outro"]:
        L.append(f"  {p['total'] - p['outro']:6.2f}—{p['total']:<6.2f} 片尾卡")
    L += ["", "  逐拍（浮窗窗口 / 旁白起点）"]
    for be in p["beats"]:
        L.append(f"   {be['idx']:>2}  {p['intro'] + be['start']:6.2f}—"
                 f"{p['intro'] + be['start'] + be['dur']:<6.2f} 旁白"
                 f"{p['intro'] + be['voice_start']:6.2f}起"
                 + (f"  {be['voice']:.2f}s" if be["voice"] else ""))
    if b:
        L += ["", f"  底板：{b['kind']}（中间段需要{p['middle_need']:.2f}s）"]
        for name, ss, d in b["segs"]:
            L.append(f"    {name:<10} 起{ss:6.2f}  长{d:5.2f}")
        L.append(f"    说明：{b['note']}")
    if p["warn"]:
        L.append("")
        L += [f"  ! {w}" for w in p["warn"]]
    return "\n".join(L)


def emit(p) -> str:
    s = ["# ---- plan_timeline.py --emit 生成，粘进 build 脚本常量区 ----",
         f"TARGET = {p['total']:.2f}",
         f"PAUSE = {p['pause']:.2f}",
         f"TAIL = {p['tail']:.2f}",
         f"INTRO = dict(kind='anim', src='画面/cards/intro.mp4', dur={p['intro']:.2f}, voice='')"
         if p["intro"] else "INTRO = None",
         f"OUTRO = dict(kind='card', src='画面/cards/outro.png', dur={p['outro']:.2f}, voice='')"
         if p["outro"] else "OUTRO = None",
         f"BEAT_DUR = {p['dwell']:.2f}",
         "BEATS = ["]
    for be in p["beats"]:
        s.append(f"    dict(voice='', sub='', tag='{be['idx']}', "
                 f"crop=(0, 0, 1080, 700), t_in=0.0, t_out={be['dur']:.2f}),")
    s.append("]")
    return "\n".join(s)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="竖屏教学短片时间轴规划器")
    ap.add_argument("--target", type=float, required=True, help="目标时长上限，如 30")
    ap.add_argument("--beats", type=int, required=True, help="浮窗拍数=解说句数")
    ap.add_argument("--bg", help="背景交代旁白音频（量实测；不给则用档位估值）")
    ap.add_argument("--voice", nargs="*", help="逐拍旁白音频，数量必须等于 --beats")
    ap.add_argument("--source", type=float, help="成片时长；给了就算底板够不够铺满")
    ap.add_argument("--extra", nargs="*", default=[], metavar="名:时长:源起点",
                    help="补充素材，如 温馨段:5.5:6.56")
    ap.add_argument("--pause", type=float, help="开头停顿秒数，覆盖档位默认")
    ap.add_argument("--tail", type=float, help="出片收尾秒数，覆盖档位默认")
    ap.add_argument("--chapters", type=int, help="分章数；60秒档默认2")
    ap.add_argument("--chapter-gap", type=float, default=1.4, help="章间满屏过渡秒数")
    ap.add_argument("--no-intro", action="store_true")
    ap.add_argument("--no-outro", action="store_true")
    ap.add_argument("--no-pause", action="store_true", help="不要开头停顿")
    ap.add_argument("--emit", action="store_true", help="输出可粘贴的常量块")
    a = ap.parse_args(argv)

    extra = []
    for e in a.extra:
        try:
            name, d, ss = e.split(":")
            extra.append((name, float(d), float(ss)))
        except ValueError:
            raise SystemExit(f"--extra 格式错：{e}，应为 名:时长:源起点")

    p = plan(a)
    b = plan_base(a.source, p["middle_need"], p["tail"], extra)
    print(report(p, b))
    if a.emit:
        print()
        print(emit(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
