from datetime import datetime
from core.config import GROQ_API_KEY, GROQ_MODEL
from core.database import (get_today_minutes_by_category, get_top_apps_today,
                      get_top_distractions_today, save_daily_summary)

def fmt(minutes):
    if minutes < 60:
        return f"{minutes}m"
    return f"{minutes//60}h {minutes%60}m" if minutes%60 else f"{minutes//60}h"

def focus_score(study, distract, total):
    if total == 0:
        return 0
    score = int((study/total - (distract/total)*0.5) * 100)
    return max(0, min(100, score))

def get_ai_coaching(study, distract, break_t, idle, score, top_apps, top_dist):
    if GROQ_API_KEY == "your_groq_api_key_here":
        return "Add your Groq API key in config.py to get AI coaching."
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        apps = ", ".join([f"{r['app']}({r['minutes']}min)" for r in top_apps])
        dist = ", ".join([f"{r['app']}({r['minutes']}min)" for r in top_dist])
        prompt = f"""You are a brutally honest AI life coach for Gurneev, a 16-year-old developer targeting MIT.

Today:
- Study time: {fmt(study)}
- Distraction: {fmt(distract)}
- Break: {fmt(break_t)}
- Idle: {fmt(idle)}
- Focus score: {score}/100
- Top apps: {apps or 'none'}
- Top distractions: {dist or 'none'}

Write 4-5 sentences: one thing done well, one habit that hurt, one action for tomorrow, MIT reminder. Be direct. Use real numbers."""
        r = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        return f"AI coaching unavailable: {e}"

def generate_daily_report(print_to_terminal=True):
    today = datetime.now().strftime("%Y-%m-%d")
    cats  = get_today_minutes_by_category()
    apps  = get_top_apps_today(5)
    dist  = get_top_distractions_today(3)

    study   = cats.get("study", 0)
    distract= cats.get("distraction", 0)
    break_t = cats.get("break", 0)
    idle    = cats.get("idle", 0)
    total   = study + distract + break_t + idle + cats.get("unknown", 0)
    score   = focus_score(study, distract, total)

    top_app  = apps[0]["app"] if apps else "none"
    top_dis  = dist[0]["app"] if dist else "none"
    ai       = get_ai_coaching(study, distract, break_t, idle, score, list(apps), list(dist))

    save_daily_summary(today, study, distract, break_t, idle, score, top_app, top_dis, ai)

    if print_to_terminal:
        SEP = "=" * 50
        print(f"\n{SEP}")
        print(f"  LIFETRACK — {datetime.now().strftime('%A %d %B %Y')}")
        print(SEP)
        print(f"\n  FOCUS SCORE: {score}/100")
        bar = "█"*int(score/5) + "░"*(20-int(score/5))
        print(f"  [{bar}]")
        print(f"\n  Study       {fmt(study):>10}")
        print(f"  Distraction {fmt(distract):>10}")
        print(f"  Break       {fmt(break_t):>10}")
        print(f"  Idle        {fmt(idle):>10}")
        print(f"  Total       {fmt(total):>10}")
        if apps:
            print(f"\n  TOP APPS")
            for r in apps:
                print(f"  {r['app']:<30} {fmt(r['minutes'])}")
        if dist:
            print(f"\n  DISTRACTIONS")
            for r in dist:
                print(f"  {r['app']:<30} {fmt(r['minutes'])}")
        print(f"\n  AI COACH:")
        print(f"  {ai}")
        print(f"\n{SEP}\n")

    return {"date": today, "study": study, "distraction": distract,
            "focus_score": score, "ai_report": ai}
