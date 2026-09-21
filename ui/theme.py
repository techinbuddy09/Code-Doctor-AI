"""
Visual atmosphere for Code Doctor AI.

Provides the premium black/gold/cyan visual system: an animated lightweight
background, the interactive Code Doctor AI buddy with smooth cursor-following eyes
and status bubble, and global theme CSS. Python only injects the block; the
heavy lifting is client-side HTML/CSS/JS.
"""

# ---------------------------------------------------------------------------
# Global theme CSS
# ---------------------------------------------------------------------------
THEME_CSS = """
:root{
  --cd-bg:#05060a;
  --cd-bg-2:#090a11;
  --cd-panel:#0c0d15;
  --cd-panel-2:#12141f;
  --cd-gold:#4bd2ee;
  --cd-gold-2:#a78bfa;
  --cd-cyan:#3dd6ff;
  --cd-text:#e9e7e0;
  --cd-muted:#8b8a96;
  --cd-line:#232430;
  --cd-line-gold:rgba(75,210,238,.28);
  --cd-mono:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;
}
html, body{
  background:var(--cd-bg) !important;
  color:var(--cd-text);
}
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"]{background:transparent !important;}
[data-testid="stHeader"]{background:transparent !important;}
.block-container{padding-top:1.2rem;padding-bottom:5rem;position:relative;z-index:1;}
:focus-visible{outline:2px solid var(--cd-gold) !important;outline-offset:2px;border-radius:4px;}

/* ---------------- Animated background ---------------- */
.cd-bg{position:fixed;inset:0;z-index:0;overflow:hidden;pointer-events:none;}
.cd-bg-glow{position:absolute;top:-22%;left:50%;transform:translateX(-50%);width:90vw;height:46vh;background:radial-gradient(ellipse at top,rgba(75,210,238,.13),transparent 70%);}
.cd-bg-grid{position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.022) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.022) 1px,transparent 1px);background-size:46px 46px;-webkit-mask-image:radial-gradient(ellipse at 50% 0%,#000 18%,transparent 72%);mask-image:radial-gradient(ellipse at 50% 0%,#000 18%,transparent 72%);}
.cd-bg-orb{position:absolute;border-radius:50%;filter:blur(90px);opacity:.55;will-change:transform;}
.cd-bg-orb-1{width:46vw;height:46vw;left:-13vw;top:-16vh;background:radial-gradient(circle,rgba(75,210,238,.30),transparent 70%);animation:cd-float-1 26s ease-in-out infinite;}
.cd-bg-orb-2{width:42vw;height:42vw;right:-15vw;top:22vh;background:radial-gradient(circle,rgba(61,214,255,.14),transparent 70%);animation:cd-float-2 32s ease-in-out infinite;}
.cd-bg-orb-3{width:36vw;height:36vw;left:26vw;bottom:-18vh;background:radial-gradient(circle,rgba(75,210,238,.16),transparent 70%);animation:cd-float-3 38s ease-in-out infinite;}
@keyframes cd-float-1{0%,100%{transform:translate3d(0,0,0) scale(1);}50%{transform:translate3d(7vw,5vh,0) scale(1.12);}}
@keyframes cd-float-2{0%,100%{transform:translate3d(0,0,0) scale(1.05);}50%{transform:translate3d(-6vw,7vh,0) scale(.94);}}
@keyframes cd-float-3{0%,100%{transform:translate3d(0,0,0) scale(1);}50%{transform:translate3d(4vw,-6vh,0) scale(1.1);}}
.cd-bg-particles{position:absolute;inset:0;}
.cd-bg-particles i{position:absolute;width:3px;height:3px;border-radius:50%;background:rgba(75,210,238,.6);box-shadow:0 0 8px rgba(75,210,238,.55);animation:cd-particledrift linear infinite;}
.cd-bg-particles i.cd-p-cy{background:rgba(61,214,255,.5);box-shadow:0 0 8px rgba(61,214,255,.5);}
@keyframes cd-particledrift{0%{transform:translate3d(0,-3vh,0);opacity:0;}12%{opacity:.85;}86%{opacity:.5;}100%{transform:translate3d(2.5vw,104vh,0);opacity:0;}}

/* ---------------- Rain (dense, seamless, behind UI) ----------------
   Layer z-index stack (lowest -> highest):
   .cd-bg rain/deco (0) -> main UI .block-container (1) -> sidebar content (1)
   -> buddy (60) / assistant panel (70). Every decorative layer is
   pointer-events:none so it can never intercept clicks. */
.cd-rain{position:absolute;inset:0;background-image:
    repeating-linear-gradient(180deg,rgba(110,140,168,.30) 0 1px,transparent 1px 22px),
    repeating-linear-gradient(180deg,rgba(154,178,202,.16) 0 1px,transparent 1px 31px),
    repeating-linear-gradient(180deg,rgba(75,210,238,.12) 0 1px,transparent 1px 47px);
  background-position:0 0,0 0,0 0;animation:cd-rain-fall 3.1s linear infinite;}
@keyframes cd-rain-fall{0%{background-position:0 0,0 0,0 0;}100%{background-position:0 22px,0 31px,0 47px;}}
.cd-rain-stk{position:absolute;top:-22vh;width:1px;background:linear-gradient(180deg,transparent,rgba(118,145,170,.55));animation:cd-rain-drop linear infinite;}
.cd-rain-stk.cd-rain-gold{background:linear-gradient(180deg,transparent,rgba(75,210,238,.62));}
@keyframes cd-rain-drop{0%{transform:translateY(0);}100%{transform:translateY(148vh);}}

/* ---------------- Futuristic developer decor ---------------- */
.cd-sym{position:absolute;font-family:var(--cd-mono);font-size:.72rem;line-height:1;color:rgba(75,210,238,.22);user-select:none;animation:cd-sym-drift 15s ease-in-out infinite;}
.cd-sym.cd-sym-cy{color:rgba(61,214,255,.2);}
@keyframes cd-sym-drift{0%,100%{transform:translateY(0);opacity:.3;}50%{transform:translateY(-11px);opacity:.85;}}
.cd-trace{position:absolute;height:1px;width:130px;background:linear-gradient(90deg,transparent,rgba(61,214,255,.3),rgba(75,210,238,.36),transparent);}
.cd-trace.t-v{width:1px;height:130px;background:linear-gradient(180deg,transparent,rgba(61,214,255,.28),transparent);}
.cd-trace-node{position:absolute;width:4px;height:4px;border-radius:50%;background:var(--cd-cyan);box-shadow:0 0 8px rgba(61,214,255,.75);animation:cd-node-pulse 3.4s ease-in-out infinite;}
.cd-trace-node.gold{background:var(--cd-gold);box-shadow:0 0 8px rgba(75,210,238,.8);}
@keyframes cd-node-pulse{0%,100%{opacity:.35;transform:scale(.85);}50%{opacity:1;transform:scale(1.4);}}
.cd-hudsweep{position:absolute;left:3%;right:3%;top:2vh;height:1px;background:linear-gradient(90deg,transparent,rgba(61,214,255,.18),transparent);animation:cd-sweep 8.5s ease-in-out infinite;}
@keyframes cd-sweep{0%{transform:translateY(2vh);opacity:0;}8%{opacity:.55;}88%{opacity:.55;}100%{transform:translateY(82vh);opacity:0;}}

/* ---------------- Typography / hero ---------------- */
.cd-hero{text-align:center;padding:10px 6px 2px;animation:cd-fade .5s ease;}
.cd-badge{position:relative;width:88px;height:88px;margin:0 auto 18px;display:grid;place-items:center;}
.cd-badge-core{width:64px;height:64px;border-radius:50%;background:radial-gradient(circle at 35% 28%,#2b2c3d,#0c0d16 72%);border:1px solid rgba(75,210,238,.55);display:grid;place-items:center;font-size:1.85rem;box-shadow:0 0 24px rgba(75,210,238,.28),inset 0 0 18px rgba(75,210,238,.08);}
.cd-badge::before,.cd-badge::after{content:"";position:absolute;border-radius:50%;border:1px solid rgba(75,210,238,.4);}
.cd-badge::before{width:88px;height:88px;animation:cd-pulse-ring 3.2s ease-out infinite;}
.cd-badge::after{width:76px;height:76px;animation:cd-pulse-ring 3.2s 1.05s ease-out infinite;}
@keyframes cd-pulse-ring{0%{transform:scale(.72);opacity:.9;}100%{transform:scale(1.28);opacity:0;}}
.cd-hero-kicker{font-size:.72rem;font-weight:800;letter-spacing:3px;color:var(--cd-gold);text-transform:uppercase;margin-bottom:8px;}
.cd-hero-title{font-size:clamp(2.1rem,6vw,3.7rem);font-weight:900;letter-spacing:-1px;color:var(--cd-text);margin:0;line-height:1.05;}
.cd-hero-gold{color:var(--cd-gold-2);text-shadow:0 0 22px rgba(75,210,238,.45);}
.cd-hero-sub{font-size:clamp(1rem,2.5vw,1.45rem);font-weight:700;color:#d8d2c0;letter-spacing:.5px;margin:10px 0 4px;}
.cd-hero-desc{color:var(--cd-muted);max-width:630px;margin:.5rem auto 0;font-size:.95rem;line-height:1.6;}

/* ---------------- Workflow ---------------- */
.cd-flow{display:flex;align-items:stretch;justify-content:center;gap:10px;flex-wrap:wrap;margin:26px 0 8px;}
.cd-flow-step{display:flex;align-items:center;gap:9px;background:linear-gradient(165deg,rgba(19,20,30,.82),rgba(10,11,17,.6));border:1px solid var(--cd-line);border-radius:12px;padding:10px 15px;font-size:.85rem;color:var(--cd-text);font-weight:600;transition:transform .2s ease,border-color .2s ease,box-shadow .2s ease;}
.cd-flow-step:hover{transform:translateY(-3px);border-color:var(--cd-line-gold);box-shadow:0 8px 20px rgba(0,0,0,.35),0 0 16px rgba(75,210,238,.12);}
.cd-flow-ic{font-size:1.15rem;}
.cd-flow-arrow{color:var(--cd-gold);opacity:.85;align-self:center;font-size:1.05rem;}

/* ---------------- Glass cards / upload ---------------- */
[data-testid="stVerticalBlockBorderWrapper"]{
  background:linear-gradient(165deg,rgba(18,19,28,.74),rgba(9,10,16,.6)) !important;
  -webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);
  border:1px solid rgba(75,210,238,.22) !important;
  border-radius:18px !important;
  box-shadow:0 10px 34px rgba(0,0,0,.42),inset 0 1px 0 rgba(255,255,255,.06) !important;
  transition:border-color .2s ease,box-shadow .2s ease;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover{border-color:rgba(75,210,238,.42) !important;box-shadow:0 12px 42px rgba(0,0,0,.46),0 0 28px rgba(75,210,238,.1) !important;}
.cd-upload-head{position:relative;padding:2px 0 2px 12px;border-left:3px solid var(--cd-gold);}
.cd-upload-title{font-size:1rem;font-weight:800;letter-spacing:2.4px;color:var(--cd-gold-2);text-transform:uppercase;}
.cd-upload-hint{color:var(--cd-muted);font-size:.82rem;margin:5px 0 14px;}

/* ---------------- Page heads / sections ---------------- */
.cd-page-head{animation:cd-fade .35s ease;}
.cd-page-title{font-size:1.6rem;font-weight:800;color:var(--cd-text);letter-spacing:-.3px;}
.cd-page-sub{color:var(--cd-muted);font-size:.86rem;margin-top:3px;}
.cd-page-sub code{color:var(--cd-gold-2);background:rgba(75,210,238,.1);padding:1px 7px;border-radius:6px;border:1px solid rgba(75,210,238,.22);font-family:var(--cd-mono);}
.cd-section{font-size:1.05rem;font-weight:700;color:var(--cd-gold-2);margin:.7rem 0 -.2rem;letter-spacing:.4px;}
.cd-issue-count{color:var(--cd-muted);font-size:.85rem;}
.cd-block-label{font-size:.68rem;font-weight:800;letter-spacing:2.2px;color:var(--cd-muted);text-transform:uppercase;margin:16px 0 8px;}
@keyframes cd-fade{from{opacity:0;transform:translateY(6px);}to{opacity:1;transform:none;}}

/* ---------------- Metric cards ---------------- */
.cd-metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(138px,1fr));gap:12px;}
.cd-metric{background:linear-gradient(165deg,rgba(21,22,32,.78),rgba(10,11,18,.55));border:1px solid rgba(75,210,238,.18);border-radius:14px;padding:18px 12px 14px;text-align:center;-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);box-shadow:0 6px 22px rgba(0,0,0,.38);transition:transform .2s ease,border-color .2s ease,box-shadow .2s ease;}
.cd-metric:hover{transform:translateY(-3px);border-color:rgba(75,210,238,.5);box-shadow:0 10px 26px rgba(0,0,0,.46),0 0 18px rgba(75,210,238,.12);}
.cd-metric-icon{font-size:1.2rem;opacity:.95;margin-bottom:7px;}
.cd-metric-val{font-size:1.7rem;font-weight:800;color:var(--cd-gold-2);letter-spacing:-.5px;line-height:1.1;font-variant-numeric:tabular-nums;}
.cd-metric-label{font-size:.69rem;letter-spacing:1.4px;text-transform:uppercase;color:var(--cd-muted);margin-top:7px;}

/* ---------------- Health ring ---------------- */
.cd-ring-wrap{display:flex;justify-content:center;align-items:center;padding:8px 0;}
.cd-ring{width:176px;height:176px;border-radius:50%;position:relative;display:grid;place-items:center;padding:11px;transition:filter .3s ease;}
.cd-ring:hover{filter:drop-shadow(0 0 16px rgba(75,210,238,.28));}
.cd-ring-inner{width:100%;height:100%;border-radius:50%;background:radial-gradient(circle at 50% 28%,#161724,#0a0b12 78%);display:flex;flex-direction:column;align-items:center;justify-content:center;box-shadow:inset 0 0 28px rgba(0,0,0,.6);}
.cd-ring-num{font-size:2.7rem;font-weight:900;color:var(--cd-gold-2);line-height:1;letter-spacing:-1px;}
.cd-ring-cap{color:var(--cd-muted);font-size:.78rem;margin-top:3px;}
.cd-ring-lbl{font-size:.66rem;letter-spacing:2.4px;color:var(--cd-muted);margin-top:10px;font-weight:700;}

/* ---------------- Empty states ---------------- */
.cd-empty{text-align:center;padding:28px 18px;background:linear-gradient(165deg,rgba(18,19,28,.62),rgba(9,10,16,.52));border:1px dashed rgba(75,210,238,.32);border-radius:16px;margin:8px 0;}
.cd-empty-ic{font-size:2rem;margin-bottom:10px;opacity:.95;}
.cd-empty-title{font-weight:700;color:var(--cd-text);font-size:1rem;}
.cd-empty-hint{color:var(--cd-muted);font-size:.85rem;margin-top:5px;line-height:1.5;}

/* ---------------- Status indicators ---------------- */
.cd-status-grid{display:flex;flex-direction:column;gap:3px;padding:4px 0;}
.cd-status{display:flex;align-items:center;gap:9px;padding:5px 2px;}
.cd-s-dot{width:8px;height:8px;border-radius:50%;background:#3d3d49;flex:none;}
.cd-s-label{font-size:.8rem;color:var(--cd-muted);}
.cd-status-online .cd-s-dot{background:#2ecc71;box-shadow:0 0 9px rgba(46,204,113,.85);animation:cd-blink-dot 2.6s ease-in-out infinite;}
.cd-status-online .cd-s-label{color:#c4ecd0;}
.cd-status-busy .cd-s-dot{background:var(--cd-gold);box-shadow:0 0 9px rgba(75,210,238,.9);animation:cd-blink-dot 1.3s ease-in-out infinite;}
.cd-status-busy .cd-s-label{color:#e9d9a8;}
.cd-status-error .cd-s-dot{background:#ff5c5c;box-shadow:0 0 9px rgba(255,92,92,.85);}
.cd-status-error .cd-s-label{color:#f4b0b0;}
@keyframes cd-blink-dot{0%,100%{opacity:1;}50%{opacity:.35;}}

/* ---------------- Chips ---------------- */
.cd-chips-row{display:flex;flex-wrap:wrap;gap:8px;}
.cd-chip{display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,.045);border:1px solid var(--cd-line);border-radius:999px;padding:4px 11px;font-size:.74rem;color:var(--cd-text);font-family:var(--cd-mono);white-space:nowrap;}
.cd-chip b{color:var(--cd-gold-2);}
.cd-lang-dot{width:7px;height:7px;border-radius:50%;background:var(--cd-gold);box-shadow:0 0 7px rgba(75,210,238,.8);display:inline-block;}

/* ---------------- Buttons ---------------- */
.stButton>button,.stDownloadButton>button,[data-testid^="stBaseButton"] button{
  background:linear-gradient(180deg,#181925,#10111a);
  color:var(--cd-gold-2);
  border:1px solid rgba(75,210,238,.35);
  border-radius:10px;
  font-weight:600;
  font-size:.92rem;
  letter-spacing:.2px;
  transition:background .18s ease,border-color .18s ease,box-shadow .18s ease,transform .12s ease;
}
.stButton>button:hover,[data-testid^="stBaseButton"] button:hover{
  border-color:var(--cd-gold);
  box-shadow:0 0 16px rgba(75,210,238,.28);
  color:var(--cd-gold-2);
  background:linear-gradient(180deg,#202132,#151624);
}
.stButton>button:active,[data-testid^="stBaseButton"] button:active{transform:scale(.985);}
.stButton>button:focus-visible,[data-testid^="stBaseButton"] button:focus-visible{outline:2px solid var(--cd-gold) !important;outline-offset:2px;}
.stButton>button[kind="primary"],[data-testid="stBaseButton-primary"] button{
  background:linear-gradient(180deg,var(--cd-gold-2),var(--cd-gold));
  color:#191000 !important;
  border:none;
  box-shadow:0 4px 18px rgba(75,210,238,.28),0 0 26px rgba(75,210,238,.14);
}
.stButton>button[kind="primary"]:hover,[data-testid="stBaseButton-primary"] button:hover{
  background:linear-gradient(180deg,#ffe089,var(--cd-gold));
  color:#191000 !important;
  box-shadow:0 6px 24px rgba(75,210,238,.45),0 0 32px rgba(75,210,238,.24);
  filter:brightness(1.05);
}
.stButton>button:disabled,[data-testid^="stBaseButton"] button:disabled{opacity:.5;}

/* ---------------- Inputs ---------------- */
[data-testid="stTextInput"] input,.stTextInput input,[data-testid="stTextArea"] textarea,.stTextArea textarea{
  background:rgba(9,10,16,.92) !important;
  border:1px solid var(--cd-line) !important;
  color:var(--cd-text) !important;
  border-radius:10px;
  transition:border-color .18s ease,box-shadow .18s ease;
}
[data-testid="stTextInput"]:focus-within input,[data-testid="stTextArea"]:focus-within textarea{
  border-color:var(--cd-gold) !important;
  box-shadow:0 0 0 3px rgba(75,210,238,.16),0 0 18px rgba(75,210,238,.12) !important;
}
.stSelectbox>div>div{background:#0b0c14 !important;border:1px solid var(--cd-line) !important;color:var(--cd-text) !important;border-radius:10px;}
[data-testid="stSelectbox"] [role="option"]{background:#0d0e16;color:var(--cd-text);}

/* ---------------- Expanders / tabs ---------------- */
[data-testid="stExpander"]{background:rgba(13,14,22,.55);border:1px solid var(--cd-line);border-radius:12px;margin:.4rem 0;transition:border-color .18s ease,box-shadow .18s ease;}
[data-testid="stExpander"]:hover{border-color:var(--cd-line-gold);box-shadow:0 0 14px rgba(75,210,238,.08);}
[data-testid="stExpander"] summary,[data-testid="stExpander"] .streamlit-expanderHeader{color:var(--cd-text);font-weight:600;}
.stTabs [data-baseweb="tab"]{color:var(--cd-muted);font-weight:600;}
.stTabs [aria-selected="true"]{color:var(--cd-gold-2);}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{background-color:var(--cd-gold);}

/* ---------------- Alerts / status / progress ---------------- */
[data-testid="stAlert"]{background:rgba(13,14,22,.7);border:1px solid var(--cd-line);border-radius:12px;}
[data-testid="stStatusWidget"]{background:rgba(13,14,22,.65);border:1px solid var(--cd-line-gold);border-radius:14px;padding:.2rem .6rem;}
[data-testid="stProgress"]>div{background:rgba(255,255,255,.06);border-radius:999px;}
[data-testid="stProgress"]>div>div{background:linear-gradient(90deg,var(--cd-gold-2),var(--cd-gold));}

/* ---------------- Code blocks (st.code + custom editor) ---------------- */
.stCode,.stCode pre{background:#0a0b12 !important;border:1px solid var(--cd-line);border-radius:10px;max-width:100%;overflow-x:auto;}
.cd-code{background:#0a0b12;border:1px solid var(--cd-line);border-radius:12px;overflow-x:auto;font-family:var(--cd-mono);font-size:.8rem;line-height:1.62;box-shadow:inset 0 0 20px rgba(0,0,0,.35);}
.cd-code-head{display:flex;justify-content:space-between;gap:10px;padding:9px 14px;background:rgba(255,255,255,.03);border-bottom:1px solid var(--cd-line);position:sticky;left:0;}
.cd-code-fname{color:var(--cd-gold-2);font-size:.78rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.cd-code-fmeta{color:var(--cd-muted);font-size:.7rem;white-space:nowrap;text-transform:capitalize;}
.cd-code-l{display:flex;}
.cd-code-n{flex:none;width:3.2em;text-align:right;padding-right:.9em;color:#4b4b58;user-select:none;background:#101119;border-right:1px solid var(--cd-line);}
.cd-code-c{display:block;padding:0 14px;white-space:pre;color:#d6d3c8;}
.cd-code .cd-code-l:first-child{padding-top:6px;}
.cd-code .cd-code-l:last-child{padding-bottom:6px;}
.cd-code-l.hl .cd-code-n{background:#1b1710;color:#caa24c;}
.cd-code-l.hl .cd-code-c{background:rgba(75,210,238,.1);box-shadow:inset 3px 0 0 var(--cd-gold);color:#ffe9a8;}

/* ---------------- Issue cards ---------------- */
.cd-issue{background:linear-gradient(165deg,rgba(17,18,27,.92),rgba(10,11,17,.86));border:1px solid var(--cd-line);border-radius:12px;padding:14px 14px 12px;margin:2px 0 10px;transition:border-color .2s ease,box-shadow .2s ease;}
.cd-issue:hover{border-color:var(--cd-line-gold);box-shadow:0 0 18px rgba(75,210,238,.07);}
.cd-issue.cd-sev-critical{border-color:rgba(255,108,108,.5);box-shadow:inset 3px 0 0 #ff6b6b,0 0 18px rgba(255,108,108,.08);}
.cd-issue.cd-sev-high{border-color:rgba(255,159,67,.42);box-shadow:inset 3px 0 0 #ff9f43;}
.cd-issue.cd-sev-medium{border-color:rgba(242,193,78,.4);box-shadow:inset 3px 0 0 #f2c14e;}
.cd-issue.cd-sev-low{border-color:rgba(127,179,213,.36);box-shadow:inset 3px 0 0 #7fb3d5;}
.cd-issue.cd-sev-info{border-color:rgba(154,160,166,.34);box-shadow:inset 3px 0 0 #9aa0a6;}
.cd-issue-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
.cd-issue-title{font-weight:700;color:var(--cd-text);font-size:.98rem;line-height:1.35;}
.cd-issue-badge{font-size:.66rem;font-weight:800;letter-spacing:1.2px;border-radius:6px;padding:3px 9px;text-transform:uppercase;flex:none;}
.cd-badge-critical{background:rgba(255,108,108,.14);color:#ff6b6b;border:1px solid rgba(255,108,108,.4);}
.cd-badge-high{background:rgba(255,159,67,.13);color:#ff9f43;border:1px solid rgba(255,159,67,.38);}
.cd-badge-medium{background:rgba(242,193,78,.13);color:#f2c14e;border:1px solid rgba(242,193,78,.36);}
.cd-badge-low{background:rgba(127,179,213,.12);color:#7fb3d5;border:1px solid rgba(127,179,213,.34);}
.cd-badge-info{background:rgba(154,160,166,.12);color:#9aa0a6;border:1px solid rgba(154,160,166,.3);}
.cd-issue-meta{display:flex;flex-wrap:wrap;gap:6px;margin:11px 0 9px;}
.cd-issue-desc{color:#d2cdc2;font-size:.9rem;line-height:1.58;}
.cd-detail{margin-top:13px;}
.cd-detail-label{font-size:.65rem;font-weight:800;letter-spacing:1.8px;color:var(--cd-gold);margin-bottom:6px;text-transform:uppercase;}
.cd-detail-body{color:#c6c2b8;font-size:.9rem;line-height:1.62;}
.cd-fix-block{background:#0a0b12;border:1px solid var(--cd-line-gold);border-left:3px solid var(--cd-gold);border-radius:10px;padding:12px 14px;}
.cd-fix-block code{font-family:var(--cd-mono);color:#e6d9a8;font-size:.85rem;white-space:pre-wrap;word-break:break-word;background:none;}

/* ---------------- Scanning panel ---------------- */
.cd-scan{position:relative;overflow:hidden;background:linear-gradient(170deg,#0b0c14,#08090f);border:1px solid var(--cd-line-gold);border-radius:20px;padding:36px 18px 32px;text-align:center;margin:4px 0 14px;box-shadow:0 12px 44px rgba(0,0,0,.5),0 0 44px rgba(75,210,238,.08);}
.cd-scan::after{content:"";position:absolute;left:6%;right:6%;top:10px;height:2px;background:linear-gradient(90deg,transparent,rgba(75,210,238,.9),transparent);animation:cd-scanline 2.4s ease-in-out infinite;border-radius:2px;box-shadow:0 0 14px rgba(75,210,238,.85);}
@keyframes cd-scanline{0%{transform:translateY(0);opacity:0;}14%{opacity:1;}100%{transform:translateY(150px);opacity:0;}}
.cd-scan-ring{position:relative;width:76px;height:76px;margin:0 auto 20px;}
.cd-scan-ring span{position:absolute;inset:0;border-radius:50%;border:2px solid transparent;border-top-color:var(--cd-gold);border-right-color:rgba(75,210,238,.4);animation:cd-spin 1.1s linear infinite;}
.cd-scan-ring span:nth-child(2){inset:9px;border-top-color:rgba(75,210,238,.6);border-right-color:transparent;animation-duration:1.6s;animation-direction:reverse;}
.cd-scan-ring span:nth-child(3){inset:18px;border-top-color:var(--cd-cyan);animation-duration:2.1s;}
@keyframes cd-spin{to{transform:rotate(360deg);}}
.cd-scan-title{font-size:1.12rem;font-weight:800;letter-spacing:2.5px;color:var(--cd-gold-2);}
.cd-scan-target{color:var(--cd-muted);font-size:.85rem;margin-top:9px;letter-spacing:1px;}
.cd-scan-msg{background:rgba(255,255,255,.03);border:1px solid var(--cd-line);border-left:2px solid var(--cd-gold);border-radius:10px;padding:10px 14px;color:#e3dfd0;font-size:.9rem;margin:0 0 12px;font-family:var(--cd-mono);}

/* ---------------- Sidebar ---------------- */
[data-testid="stSidebar"]{background:linear-gradient(180deg,#090a11,#07080d) !important;border-right:1px solid var(--cd-line);}
[data-testid="stSidebar"] .block-container{padding-top:1.3rem;}
.cd-side-title{font-size:.82rem;font-weight:800;letter-spacing:1.6px;text-transform:uppercase;color:var(--cd-gold-2);margin:6px 0 4px;}
.cd-logo{font-size:1.65rem;font-weight:900;letter-spacing:-.6px;color:var(--cd-gold-2);line-height:1.1;}
.cd-logo span{color:var(--cd-muted);}
[data-testid="stCheckbox"] label p{color:var(--cd-text);}

/* ---------------- Sidebar circuit deco ---------------- */
.cd-side-deco{position:absolute;inset:0;z-index:0;pointer-events:none;overflow:hidden;}
.cd-side-deco .cd-trace-node{margin-left:-2px;margin-top:-2px;}
.cd-side-sym{position:absolute;font-family:var(--cd-mono);font-size:.72rem;color:rgba(75,210,238,.18);user-select:none;animation:cd-sym-drift 16s ease-in-out infinite;}
.cd-side-spark{position:absolute;width:3px;height:3px;border-radius:50%;background:rgba(61,214,255,.55);box-shadow:0 0 8px rgba(61,214,255,.7);animation:cd-node-pulse 3.8s ease-in-out infinite;}
.cd-side-bracket{position:absolute;width:14px;height:14px;border:1px solid rgba(75,210,238,.22);}
.cd-side-bracket.br-tl{left:12px;top:16px;border-right:0;border-bottom:0;}
.cd-side-bracket.br-bl{left:12px;bottom:16px;border-right:0;border-top:0;}
.cd-side-bracket.br-tr{right:12px;top:16px;border-left:0;border-bottom:0;}
.cd-side-bracket.br-br{right:12px;bottom:16px;border-left:0;border-top:0;}

/* ---------------- Buddy ---------------- */
.cd-buddy-wrap{position:fixed;right:20px;bottom:20px;z-index:60;display:flex;flex-direction:column;align-items:center;cursor:pointer;user-select:none;-webkit-user-select:none;pointer-events:none;}
.cd-buddy{width:74px;height:74px;pointer-events:auto;transition:width .25s cubic-bezier(.2,.8,.3,1),height .25s cubic-bezier(.2,.8,.3,1),filter .25s ease;animation:cd-breathe 4.2s ease-in-out infinite;filter:drop-shadow(0 0 10px rgba(75,210,238,.18));}
.cd-buddy-wrap:hover .cd-buddy{width:82px;height:82px;filter:drop-shadow(0 0 16px rgba(75,210,238,.4));}
.cd-buddy.clicked{animation:cd-pulse .5s ease;}
@keyframes cd-breathe{0%,100%{transform:scale(1);}50%{transform:scale(1.045);}}
@keyframes cd-pulse{0%{transform:scale(1);}30%{transform:scale(.9);}60%{transform:scale(1.07);}100%{transform:scale(1);}}
.cd-buddy-wrap::after{content:"";position:absolute;top:6px;left:50%;transform:translateX(-50%);width:96px;height:96px;border-radius:50%;background:radial-gradient(circle,rgba(75,210,238,.26),transparent 70%);filter:blur(7px);animation:cd-glowpulse 4.2s ease-in-out infinite;pointer-events:none;}
@keyframes cd-glowpulse{0%,100%{opacity:.5;transform:translateX(-50%) scale(1);}50%{opacity:1;transform:translateX(-50%) scale(1.1);}}
.cd-buddy-aura{position:absolute;inset:0;pointer-events:none;}
.cd-buddy-ring{position:absolute;left:50%;top:50%;width:98px;height:98px;margin-left:-49px;margin-top:-49px;border-radius:50%;border:1px dashed rgba(75,210,238,.4);animation:cd-spin 20s linear infinite;}
.cd-buddy-arc{position:absolute;left:50%;top:50%;width:116px;height:116px;margin-left:-58px;margin-top:-58px;border-radius:50%;background:conic-gradient(from 210deg,rgba(61,214,255,0) 0 40deg,rgba(75,210,238,.32) 52deg 82deg,rgba(61,214,255,.2) 90deg 112deg,rgba(61,214,255,0) 120deg 360deg);-webkit-mask:radial-gradient(circle,transparent 0 48px,#000 49px 58px,transparent 59px);mask:radial-gradient(circle,transparent 0 48px,#000 49px 58px,transparent 59px);animation:cd-spin 11s linear reverse infinite;}
.cd-buddy-corner{position:absolute;width:11px;height:11px;border:1px solid rgba(75,210,238,.55);}
.cd-buddy-corner.c1{left:-3px;top:-3px;border-right:0;border-bottom:0;border-top-left-radius:4px;}
.cd-buddy-corner.c4{right:-3px;bottom:-3px;border-left:0;border-top:0;border-bottom-right-radius:4px;}
.cd-buddy .cd-eye{transform-box:fill-box;transform-origin:center;animation:cd-blink 5.4s 1.4s infinite;}
@keyframes cd-blink{0%,90%,100%{transform:scaleY(1);}93%{transform:scaleY(.12);}96%{transform:scaleY(1);}}
.cd-buddy-tip{color:#cfcbbf;font-size:.72rem;background:rgba(14,14,21,.9);border:1px solid var(--cd-line);border-radius:8px;padding:3px 9px;margin-top:7px;white-space:nowrap;opacity:0;transform:translateY(3px);transition:opacity .2s ease,transform .2s ease;pointer-events:none;}
.cd-buddy-wrap:hover .cd-buddy-tip{opacity:1;transform:none;}
.cd-bubble{position:absolute;bottom:calc(100% + 10px);width:max-content;max-width:230px;background:rgba(13,14,22,.94);border:1px solid var(--cd-line-gold);border-radius:10px;padding:6px 12px;font-size:.74rem;color:#e6dfc8;box-shadow:0 8px 22px rgba(0,0,0,.5);pointer-events:none;animation:cd-bubble-in 6.5s ease forwards;}
.cd-bubble::after{content:"";position:absolute;top:100%;left:50%;transform:translateX(-50%);border:6px solid transparent;border-top-color:rgba(75,210,238,.5);}
@keyframes cd-bubble-in{0%{opacity:0;transform:translateY(5px);}5%{opacity:1;transform:none;}84%{opacity:1;}100%{opacity:0;}}
.cd-buddy-wrap:hover .cd-bubble{opacity:1;transform:none;animation:none;}

/* ---------------- Assistant panel ---------------- */
.cd-panel{position:fixed;right:22px;bottom:108px;width:300px;max-height:424px;z-index:70;background:#0c0d15;border:1px solid rgba(75,210,238,.38);border-radius:14px;padding:14px;box-shadow:0 12px 38px rgba(0,0,0,.62),0 0 24px rgba(75,210,238,.06);transform:translateY(12px);opacity:0;pointer-events:none;transition:transform .22s ease,opacity .22s ease;display:flex;flex-direction:column;font-size:.9rem;}
.cd-panel.open{transform:none;opacity:1;pointer-events:auto;}
.cd-p-head{font-weight:700;color:var(--cd-gold-2);margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;}
.cd-p-close{background:none;border:none;color:var(--cd-muted);font-size:1.1rem;cursor:pointer;}
.cd-p-close:focus-visible,.cd-p-close:hover{color:var(--cd-gold-2);}
.cd-p-body{color:var(--cd-text);overflow-y:auto;line-height:1.55;}
.cd-p-foot{margin-top:10px;color:var(--cd-muted);font-size:.73rem;border-top:1px solid var(--cd-line);padding-top:6px;}

/* ---------------- Scrollbars ---------------- */
::-webkit-scrollbar{width:10px;height:10px;}
::-webkit-scrollbar-track{background:#07070c;}
::-webkit-scrollbar-thumb{background:#2b2b38;border-radius:6px;}
::-webkit-scrollbar-thumb:hover{background:#3c3c4c;}

/* ---------------- Responsive ---------------- */
@media (max-width:720px){
  .block-container{padding-left:1rem !important;padding-right:1rem !important;}
  .cd-scan-ring{width:60px;height:60px;}
  .cd-panel{width:min(300px,calc(100vw - 30px));right:16px;bottom:96px;}
  .cd-buddy-wrap{right:14px;bottom:14px;}
  .cd-buddy{width:60px;height:60px;}
  .cd-buddy-wrap:hover .cd-buddy{width:66px;height:66px;}
  .cd-buddy-wrap::after{width:76px;height:76px;}
  .cd-code-fname{max-width:55vw;}
}
@media (max-width:560px){
  .cd-flow{flex-direction:column;align-items:stretch;}
  .cd-flow-arrow{transform:rotate(90deg);margin:0;text-align:center;}
  .cd-metrics{grid-template-columns:repeat(auto-fit,minmax(118px,1fr));}
}

/* ---------------- Reduced motion ---------------- */
@media (prefers-reduced-motion: reduce){
  *,*::before,*::after{animation-duration:.01ms !important;animation-iteration-count:1 !important;transition-duration:.01ms !important;scroll-behavior:auto !important;}
  .cd-bg-orb,.cd-bg-particles,.cd-rain,.cd-rain-stk,.cd-rain-gold,.cd-sym,.cd-hudsweep,.cd-scan::after,.cd-badge::before,.cd-badge::after,.cd-buddy-ring,.cd-buddy-arc{display:none !important;}
  .cd-buddy,.cd-buddy-wrap::after,.cd-buddy .cd-eye,.cd-trace-node,.cd-side-spark,.cd-side-sym{animation:none !important;}
}
"""


def inject_visuals(backend_status: str = "Ready.", status_kind: str = "ready"):
    """Inject shared styles and the CSS-only workspace presentation."""
    from pathlib import Path
    workspace_css = Path(__file__).with_name("workspace.css").read_text(encoding="utf-8")
    return "<style>" + THEME_CSS + workspace_css + "</style>"
