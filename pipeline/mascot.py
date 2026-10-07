import html

DEFAULT_MESSAGES = {
    "idle": (
        "Hi, I'm Tasky! Drop in a meeting recording or try the sample.\n"
    ),
    "working": (
        "Listening carefully...\n\n"
        "• Converting speech to raw text\n"
        "• Refining technical jargon safely\n"
        "• Verifying evidence timestamps"
    ),
    "done": (
        " All done! Here is how to navigate your results:\n\n"
        "•  Overview: Quick summary & top action items\n"
        "•  Transcripts: Raw vs. refined diffs & search\n"
        "•  Minutes: Topic-by-topic discussion\n"
        "•  Decisions & Actions: Timestamped evidence audit\n"
        "• ⬇ Downloads: Export to MD, JSON, or ZIP"
    ),
    "error": (
        "Oops, something went wrong!\n\n"
        "Please verify your API keys, audio file format, or model choices and try again."
    ),
}

TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
html,body{margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;}
.wrap{display:flex;align-items:center;justify-content:center;gap:16px;padding:6px 10px;}
svg{width:150px;height:165px;overflow:visible;display:block;flex:none;}
.bubble{position:relative;background:#fff;color:#2B2550;border:2px solid #E3DCFF;border-radius:18px;padding:12px 16px;font-size:14px;line-height:1.45;max-width:380px;box-shadow:0 3px 10px rgba(80,60,160,.15);animation:bubblepop .5s ease-out;white-space:pre-line;}
.bubble:before{content:"";position:absolute;left:-11px;top:50%;margin-top:-9px;border-style:solid;border-width:9px 10px 9px 0;border-color:transparent #E3DCFF transparent transparent;}
.bubble:after{content:"";position:absolute;left:-7px;top:50%;margin-top:-7px;border-style:solid;border-width:7px 8px 7px 0;border-color:transparent #fff transparent transparent;}
@keyframes bubblepop{0%{transform:scale(.85);opacity:0}100%{transform:scale(1);opacity:1}}

.hero{transform-box:view-box;transform-origin:100px 200px;}
.idle .hero{animation:bounce 2.2s ease-in-out infinite;}
.working .hero{animation:rock .9s ease-in-out infinite;}
.done .hero{animation:jump .7s ease-out 3,bounce 2.2s ease-in-out 2.1s infinite;}
.error .hero{animation:shake .45s ease-in-out 3;}
@keyframes bounce{0%,100%{transform:translateY(0)}50%{transform:translateY(-8px)}}
@keyframes rock{0%,100%{transform:rotate(-4deg)}50%{transform:rotate(4deg)}}
@keyframes jump{0%{transform:translateY(0) scale(1,1)}30%{transform:translateY(0) scale(1.05,.93)}60%{transform:translateY(-24px) scale(.97,1.04)}100%{transform:translateY(0) scale(1,1)}}
@keyframes shake{0%,100%{transform:translateX(0)}25%{transform:translateX(-6px)}75%{transform:translateX(6px)}}

.shadow{transform-box:fill-box;transform-origin:center;}
.idle .shadow{animation:shadowpulse 2.2s ease-in-out infinite;}
.done .shadow{animation:shadowpulse .7s ease-out 3;}
@keyframes shadowpulse{0%,100%{transform:scale(1)}50%{transform:scale(.85)}}

.eyes{transform-box:fill-box;transform-origin:center;animation:blink 4s infinite;}
@keyframes blink{0%,92%,100%{transform:scaleY(1)}95%{transform:scaleY(.08)}}

.arm-l{transform-box:view-box;transform-origin:42px 135px;}
.arm-r{transform-box:view-box;transform-origin:158px 135px;}
.idle .arm-l{animation:wave 1.4s ease-in-out infinite;}
.working .arm-l{animation:sway 1s ease-in-out infinite;}
.working .arm-r{animation:sway 1s ease-in-out infinite reverse;}
.done .arm-l{animation:cheer .5s ease-in-out infinite;}
.done .arm-r{animation:cheerr .5s ease-in-out infinite;}
@keyframes wave{0%,100%{transform:rotate(115deg)}50%{transform:rotate(145deg)}}
@keyframes sway{0%,100%{transform:rotate(-6deg)}50%{transform:rotate(6deg)}}
@keyframes cheer{0%,100%{transform:rotate(135deg)}50%{transform:rotate(165deg)}}
@keyframes cheerr{0%,100%{transform:rotate(-135deg)}50%{transform:rotate(-165deg)}}

.waves,.sparkles,.badge,.sweat,.mouth-talk,.mouth-frown,.mouth-big{display:none;}
.working .waves,.working .mouth-talk{display:inline;}
.done .sparkles,.done .badge,.done .mouth-big{display:inline;}
.error .sweat,.error .mouth-frown{display:inline;}
.working .mouth-smile,.done .mouth-smile,.error .mouth-smile{display:none;}

.mouth-talk{transform-box:fill-box;transform-origin:center;animation:talk .35s ease-in-out infinite;}
@keyframes talk{0%,100%{transform:scaleY(.5)}50%{transform:scaleY(1.1)}}
.bar{transform-box:fill-box;transform-origin:center;animation:eq .8s ease-in-out infinite;}
.bar:nth-child(2){animation-delay:.2s;}
.bar:nth-child(3){animation-delay:.4s;}
@keyframes eq{0%,100%{transform:scaleY(.4)}50%{transform:scaleY(1.2)}}
.spark{transform-box:fill-box;transform-origin:center;animation:twinkle 1s ease-in-out infinite;}
.spark.s2{animation-delay:.3s;}
.spark.s3{animation-delay:.6s;}
@keyframes twinkle{0%,100%{transform:scale(.3);opacity:.4}50%{transform:scale(1.1);opacity:1}}
.badge{transform-box:fill-box;transform-origin:center;animation:badgepop .5s ease-out;}
@keyframes badgepop{0%{transform:scale(0)}70%{transform:scale(1.2)}100%{transform:scale(1)}}
.sweat{animation:drip 1.2s ease-in infinite;}
@keyframes drip{0%{transform:translateY(0);opacity:1}100%{transform:translateY(22px);opacity:0}}
</style></head>
<body>
<div class="wrap __STATE__">
<svg viewBox="0 0 200 220" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Tasky the mascot">
  <ellipse class="shadow" cx="100" cy="208" rx="52" ry="8" fill="#000" opacity=".12"/>
  <g class="hero">
    <ellipse class="arm-r" cx="158" cy="157" rx="10" ry="22" fill="#6A49F0"/>
    <ellipse class="arm-l" cx="42" cy="157" rx="10" ry="22" fill="#6A49F0"/>
    <ellipse cx="78" cy="192" rx="19" ry="9" fill="#FF9F43"/>
    <ellipse cx="122" cy="192" rx="19" ry="9" fill="#FF9F43"/>
    <ellipse cx="100" cy="120" rx="62" ry="72" fill="#7C5CFF"/>
    <ellipse cx="100" cy="148" rx="40" ry="40" fill="#B9A8FF"/>
    <path d="M 40 104 Q 40 44 100 44 Q 160 44 160 104" stroke="#FFC83D" stroke-width="8" fill="none" stroke-linecap="round"/>
    <rect x="32" y="92" width="18" height="36" rx="9" fill="#FFC83D"/>
    <rect x="150" y="92" width="18" height="36" rx="9" fill="#FFC83D"/>
    <path d="M 41 126 Q 44 156 76 148" stroke="#FFC83D" stroke-width="4" fill="none" stroke-linecap="round"/>
    <circle cx="80" cy="147" r="6" fill="#FFC83D"/>
    <g class="eyes">
      <circle cx="78" cy="96" r="16" fill="#fff"/>
      <circle cx="122" cy="96" r="16" fill="#fff"/>
      <circle cx="81" cy="98" r="7.5" fill="#1F1B3A"/>
      <circle cx="125" cy="98" r="7.5" fill="#1F1B3A"/>
      <circle cx="83.5" cy="95" r="2.6" fill="#fff"/>
      <circle cx="127.5" cy="95" r="2.6" fill="#fff"/>
    </g>
    <circle cx="60" cy="122" r="7" fill="#FF9CC2" opacity=".85"/>
    <circle cx="140" cy="122" r="7" fill="#FF9CC2" opacity=".85"/>
    <path class="mouth-smile" d="M 86 124 Q 100 140 114 124" stroke="#1F1B3A" stroke-width="4.5" fill="none" stroke-linecap="round"/>
    <path class="mouth-big" d="M 84 122 Q 100 150 116 122 Z" fill="#1F1B3A" stroke="#1F1B3A" stroke-width="3" stroke-linejoin="round"/>
    <ellipse class="mouth-talk" cx="100" cy="132" rx="11" ry="9" fill="#1F1B3A"/>
    <path class="mouth-frown" d="M 88 136 Q 100 124 112 136" stroke="#1F1B3A" stroke-width="4.5" fill="none" stroke-linecap="round"/>
    <g class="badge">
      <circle cx="100" cy="162" r="14" fill="#2ECC71"/>
      <path d="M 92 162 L 98 168 L 109 156" stroke="#fff" stroke-width="4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
    </g>
    <g class="waves">
      <rect class="bar" x="84" y="14" width="6" height="22" rx="3" fill="#FFC83D"/>
      <rect class="bar" x="100" y="14" width="6" height="22" rx="3" fill="#FFC83D"/>
      <rect class="bar" x="116" y="14" width="6" height="22" rx="3" fill="#FFC83D"/>
    </g>
    <path class="sweat" d="M 150 66 Q 157 80 150 88 Q 143 80 150 66 Z" fill="#7FD3FF"/>
  </g>
  <g class="sparkles">
    <g transform="translate(26,52)"><path class="spark" d="M0,-10 L3,-3 L10,0 L3,3 L0,10 L-3,3 L-10,0 L-3,-3 Z" fill="#FFC83D"/></g>
    <g transform="translate(176,64)"><path class="spark s2" d="M0,-10 L3,-3 L10,0 L3,3 L0,10 L-3,3 L-10,0 L-3,-3 Z" fill="#FF9CC2"/></g>
    <g transform="translate(160,18)"><path class="spark s3" d="M0,-10 L3,-3 L10,0 L3,3 L0,10 L-3,3 L-10,0 L-3,-3 Z" fill="#7FD3FF"/></g>
  </g>
</svg>
<div class="bubble">__MESSAGE__</div>
</div>
</body></html>
"""


def mascot_html(state="idle", message=None):
    if state not in DEFAULT_MESSAGES:
        state = "idle"
    text = html.escape(message or DEFAULT_MESSAGES[state])
    return TEMPLATE.replace("__STATE__", state).replace("__MESSAGE__", text)


def show_mascot(state="idle", message=None, height=230):
    import streamlit as st
    doc = mascot_html(state, message)
    if hasattr(st, "iframe"):
        st.iframe(doc, height=height)
    else:
        import streamlit.components.v1 as components
        components.html(doc, height=height)