"""
Demo Data Seeder for MemoryGraph.

Creates a rich, realistic 35-session demo dataset following Alex's
6-month life story arc for video recording / demo purposes.

Usage:
    python scripts/seed_demo.py            # build fixtures only
    python scripts/seed_demo.py --run       # build fixtures + ingest into HydraDB
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Path setup
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))

FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"
SESSIONS_FILE = FIXTURES_DIR / "sample_sessions.json"
QUESTIONS_FILE = FIXTURES_DIR / "sample_questions.json"


# ── Session construction helpers ──────────────────────────────────────────

def build_sessions() -> list[dict]:
    """Build the 35-session Alex story arc.

    Timestamps start 2024-01-15 and are spaced ~5 days apart.
    Each session has 4-6 conversational messages.
    """
    start = datetime(2024, 1, 15, 10, 30, 0)
    sessions: list[dict] = []
    session_id = 0

    def add(days_offset: int, messages: list[tuple[str, str]]):
        nonlocal session_id
        session_id += 1
        ts = start + timedelta(days=days_offset)
        sessions.append({
            "session_id": f"alex-session-{session_id}",
            "user_id": "alex",
            "started_at": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "messages": [
                {"role": role, "content": content}
                for role, content in messages
            ],
        })

    # ── Month 1 (Sessions 1-6): Rajshahi life ──
    add(0, [
        ("user", "Hi, I'm Alex. I live in Rajshahi and work as a software engineer."),
        ("assistant", "Nice to meet you, Alex! Rajshahi is a lovely city. What kind of software do you build?"),
        ("user", "Mostly backend services in Python. Oh, and I have a dog named Mochi — he's a golden retriever."),
        ("assistant", "A golden retriever named Mochi! That's adorable. Does he keep you company while you code?"),
        ("user", "Yeah, he sleeps under my desk. I'm single, by the way, and I really enjoy hiking on weekends."),
        ("assistant", "Hiking sounds like a great way to unwind. Any favorite trails near Rajshahi?"),
    ])
    add(5, [
        ("user", "I'm cooking a new curry recipe tonight, feeling pretty good about it."),
        ("assistant", "Curry is a great choice! What's the star ingredient?"),
        ("user", "Chicken with a lot of spices. Cooking helps me relax after work."),
        ("assistant", "Nothing beats a home-cooked meal. Enjoy your evening!"),
    ])
    add(10, [
        ("user", "Heads up — I have a big project deadline next week. Kind of stressed."),
        ("assistant", "That's a tight timeline. Want to talk through how to break it down?"),
        ("user", "Maybe later. I also caught a cold this week, feeling pretty wiped out."),
        ("assistant", "Sorry to hear that. Rest up and drink plenty of fluids — the deadline will wait."),
    ])
    add(15, [
        ("user", "Mochi and I went hiking near the river today. Felt nice to get outside."),
        ("assistant", "Glad you're feeling well enough for a hike! How's the cold?"),
        ("user", "Better, thanks. Still coughing a bit but the fresh air helped."),
        ("assistant", "Glad to hear it's improving. Take it easy."),
    ])
    add(20, [
        ("user", "The project is coming together. I think I'll hit the deadline."),
        ("assistant", "That's great progress! You've got this."),
        ("user", "Thanks. Mochi chewed my favorite shoe again though, little gremlin."),
        ("assistant", "Haha, classic retriever behavior. He keeps life interesting!"),
    ])
    add(25, [
        ("user", "Quiet weekend, just cooked and watched movies with Mochi."),
        ("assistant", "Sounds peaceful. Any movie recommendations?"),
        ("user", "Nothing fancy, just comfort stuff. I've been meaning to plan a trip somewhere."),
        ("assistant", "A trip sounds nice. Anywhere in mind?"),
        ("user", "Not yet. Maybe the coast someday."),
    ])

    # ── Month 2 (Sessions 7-12): Loss and change ──
    add(30, [
        ("user", "Mochi seems off today, not eating much. I'm a bit worried."),
        ("assistant", "That's concerning. Have you been able to get him to a vet?"),
        ("user", "Booked one for tomorrow. Hoping it's nothing serious."),
        ("assistant", "Fingers crossed for Mochi. Keep me posted."),
    ])
    add(35, [
        ("user", "Took Mochi to the vet, they're running tests. He's lethargic."),
        ("assistant", "I'm sorry, that sounds scary. Sending good thoughts your way."),
        ("user", "Thanks. The cold is finally gone at least, so that's something."),
        ("assistant", "Small wins. Hope Mochi pulls through."),
    ])
    add(40, [
        ("user", "Mochi's tests came back, they're treating him but he's weak."),
        ("assistant", "I hope the treatment helps quickly. How are you holding up?"),
        ("user", "Not great, honestly. Project deadline passed though — shipped it on time."),
        ("assistant", "Proud of you for shipping under stress. And hoping Mochi recovers."),
    ])
    add(45, [
        ("user", "I'm devastated... Mochi passed away last night. I don't know what to do."),
        ("assistant", "I'm so, so sorry, Alex. Losing Mochi is a deep loss. Be gentle with yourself."),
        ("user", "Thank you. He was my best friend for years."),
        ("assistant", "He clearly meant the world to you. However you need to grieve is okay."),
        ("user", "I've been thinking maybe I should move to Dhaka, be closer to friends."),
        ("assistant", "A fresh start can help. Dhaka's a big change from Rajshahi though."),
    ])
    add(50, [
        ("user", "Still processing Mochi. Went for a long walk instead of hiking."),
        ("assistant", "That sounds grounding. Take all the time you need."),
        ("user", "I think I'll start looking at apartments in Dhaka next month."),
        ("assistant", "Whenever you're ready. No rush."),
    ])
    add(55, [
        ("user", "Found a few listings in Dhaka. Exciting but scary."),
        ("assistant", "Big move! What neighborhood are you leaning toward?"),
        ("user", "Something central, near the office. The cold is long gone now, thankfully."),
        ("assistant", "Good, health first. Central Dhaka has nice cafes too."),
    ])

    # ── Month 3 (Sessions 13-18): New beginnings ──
    add(60, [
        ("user", "Packing up the Rajshahi place. Bittersweet."),
        ("assistant", "Completely understandable. Six months ago Mochi was here with you."),
        ("user", "Yeah. But I'm ready for what's next."),
        ("assistant", "That's a healthy place to be. Safe travels with the move."),
    ])
    add(65, [
        ("user", "I moved to Dhaka! New apartment, central and sunny."),
        ("assistant", "Congratulations on the move! How's the new place?"),
        ("user", "Small but cozy. Different vibe from Rajshahi, busier streets."),
        ("assistant", "You'll settle in. Any favorite spot yet?"),
    ])
    add(70, [
        ("user", "Got promoted to senior engineer today! Same team, more scope."),
        ("assistant", "That's fantastic, Alex — senior engineer, well deserved!"),
        ("user", "Thanks. Feels good after everything this year."),
        ("assistant", "You've earned it. Celebrate a little!"),
    ])
    add(75, [
        ("user", "Exploring Dhaka, found a great coffee roaster nearby."),
        ("assistant", "Nice! Exploring a new city one cafe at a time."),
        ("user", "I'm feeling a lot better lately, more like myself."),
        ("assistant", "That's wonderful to hear. The move agreed with you."),
    ])
    add(80, [
        ("user", "I adopted a cat! Her name is Pixel, she's a rescue."),
        ("assistant", "A cat named Pixel — love it! How are you two getting on?"),
        ("user", "She's shy but sweet. Different from Mochi but good company."),
        ("assistant", "Rescue cats have the best personalities. Give Pixel scritches from me."),
    ])
    add(85, [
        ("user", "Planning a vacation to Cox's Bazar next month, first real break."),
        ("assistant", "Cox's Bazar — the long beach! Well deserved after the year you've had."),
        ("user", "Yeah, Pixel will stay with a friend while I'm gone."),
        ("assistant", "She'll be fine. You enjoy the sea."),
    ])

    # ── Month 4 (Sessions 19-24): Connection ──
    add(90, [
        ("user", "Met someone at a meetup — her name is Sara. We really hit it off."),
        ("assistant", "That's lovely, Alex! What's she like?"),
        ("user", "She's a designer, funny, into photography. We exchanged numbers."),
        ("assistant", "Sounds promising. Happy for you."),
    ])
    add(95, [
        ("user", "On vacation in Cox's Bazar now — the beach is incredible."),
        ("assistant", "So glad you made it! How's the weather?"),
        ("user", "Sunny and warm. Pixel is with my friend, hopefully behaving."),
        ("assistant", "Enjoy every minute. You earned this trip."),
    ])
    add(100, [
        ("user", "Back from Cox's Bazar, already missing the ocean."),
        ("assistant", "Welcome back! How was the whole trip?"),
        ("user", "Perfect. And Sara and I went on a date — it went really well."),
        ("assistant", "A date with Sara! Things are moving nicely."),
    ])
    add(105, [
        ("user", "Sara and I are officially dating. Feels early but right."),
        ("assistant", "Congratulations! Dating Sara — wishing you both the best."),
        ("user", "Thanks. Pixel is terrified of water though, funny little thing."),
        ("assistant", "Haha, good thing you're not taking Pixel to the beach!"),
    ])
    add(110, [
        ("user", "Started learning guitar, just basics so far."),
        ("assistant", "Guitar! Any song you're aiming for?"),
        ("user", "Nothing fancy, just campfire chords. Pixel judges me from the sofa."),
        ("assistant", "Pixel's a tough critic. Keep at it!"),
    ])
    add(115, [
        ("user", "Sara came over, Pixel hid under the bed the whole time."),
        ("assistant", "Shy kitty! She'll warm up eventually."),
        ("user", "Probably. We cooked dinner together, it was nice."),
        ("assistant", "Cooking with Sara — sounds like a good evening."),
    ])

    # ── Month 5 (Sessions 25-30): Growth ──
    add(120, [
        ("user", "Work's busy, but I got promoted to tech lead this week!"),
        ("assistant", "Tech lead! Big step up from senior engineer — congratulations, Alex!"),
        ("user", "Thanks. Leading the team now, a bit nervous but excited."),
        ("assistant", "You'll do great. From software engineer to tech lead in six months!"),
    ])
    add(125, [
        ("user", "Sara and I got engaged! She said yes last night."),
        ("assistant", "Oh my goodness, congratulations! Engaged to Sara — amazing news!"),
        ("user", "Thanks. Still can't believe it. Pixel sat on the ring box, typical."),
        ("assistant", "Haha, Pixel oversaw the proposal. Wonderful news for you both."),
    ])
    add(130, [
        ("user", "We're planning the wedding for next year, spring maybe."),
        ("assistant", "A spring wedding — beautiful. Starting early is smart."),
        ("user", "Lots to figure out. Venue, guest list, the works."),
        ("assistant", "Exciting times ahead. Enjoy the planning."),
    ])
    add(135, [
        ("user", "Pixel loves sleeping on my keyboard while I work. Annoying but cute."),
        ("assistant", "Classic cat behavior! She's claimed your desk as hers."),
        ("user", "Yeah. I've switched from cooking to baking lately, made bread."),
        ("assistant", "Baking bread is satisfying. Trading curry for sourdough?"),
    ])
    add(140, [
        ("user", "Baked a cake for Sara's birthday, turned out decent."),
        ("assistant", "A homemade birthday cake — she'll love it."),
        ("user", "She did. We're thinking bigger apartment after the wedding."),
        ("assistant", "Makes sense, more space for two plus Pixel."),
    ])
    add(145, [
        ("user", "Guitar practice going okay, can play a full song now."),
        ("assistant", "Progress! Pixel approves now?"),
        ("user", "Still judges, but less. Career's good, life's good."),
        ("assistant", "Glad to hear it. You've come a long way this year."),
    ])

    # ── Month 6 (Sessions 31-35): Settling ──
    add(150, [
        ("user", "Wedding venue's booked for next April. Feels real now."),
        ("assistant", "April wedding, booked — that's a milestone! Congrats again."),
        ("user", "Yeah. Sara's thrilled. I started a side project too, a small app."),
        ("assistant", "A side project on top of tech lead? Ambitious! What's it do?"),
    ])
    add(155, [
        ("user", "Side project is a habit tracker, just for fun."),
        ("assistant", "Nice — dogfood your own tool. How's it coming?"),
        ("user", "Slow but steady. I want to move to a bigger apartment soon."),
        ("assistant", "More room for the soon-to-be family. Reasonable."),
    ])
    add(160, [
        ("user", "Looked at a bigger place near the park, love it."),
        ("assistant", "Near the park sounds great for walks. Put in an offer?"),
        ("user", "Not yet, but soon. Pixel would have a garden finally."),
        ("assistant", "Pixel's going to love a garden. Keep me posted."),
    ])
    add(165, [
        ("user", "Pixel has a vet appointment next week, just a checkup."),
        ("assistant", "Routine checkup, good to stay on top of it."),
        ("user", "Yeah. Hard to believe it's been six months since the move."),
        ("assistant", "Time flies. You've built a whole new life here."),
    ])
    add(170, [
        ("user", "Reflecting on the past 6 months — a lot happened."),
        ("assistant", "You're not wrong. Want to look back at the highlights?"),
        ("user", "Lost Mochi, moved to Dhaka, met Sara, got engaged, two promotions..."),
        ("assistant", "Quite a journey. From Rajshahi to tech lead and engaged — remarkable."),
        ("user", "Yeah. Grateful for where things are now."),
        ("assistant", "Well earned, Alex. Here's to the next six months."),
    ])

    return sessions


def build_questions() -> list[dict]:
    """Build 20 evaluation questions covering all fact types."""
    return [
        # ── Current facts ──
        {"question": "Where does Alex live now?", "expected_answer": "Dhaka", "expected_confidence_min": 0.7},
        {"question": "What is Alex's current job title?", "expected_answer": "tech lead", "expected_confidence_min": 0.7},
        {"question": "Who is Alex engaged to?", "expected_answer": "Sara", "expected_confidence_min": 0.7},
        {"question": "What pet does Alex have now?", "expected_answer": "cat named Pixel", "expected_confidence_min": 0.7},
        {"question": "What is Alex's current hobby?", "expected_answer": "baking", "expected_confidence_min": 0.5},

        # ── Historical facts ──
        {"question": "Where did Alex live before Dhaka?", "expected_answer": "Rajshahi", "expected_confidence_min": 0.6},
        {"question": "What was Alex's first job title in this story?", "expected_answer": "software engineer", "expected_confidence_min": 0.6},
        {"question": "What was Alex's pet before Pixel?", "expected_answer": "dog named Mochi", "expected_confidence_min": 0.6},

        # ── Overwritten / superseded facts ──
        {"question": "What pet does Alex have?", "expected_answer": "cat Pixel", "expected_confidence_min": 0.7,
         "note": "Dog Mochi died — must return current pet, not Mochi"},
        {"question": "Is Alex still a software engineer?", "expected_answer": "no, tech lead", "expected_confidence_min": 0.5},
        {"question": "Does Alex still live in Rajshahi?", "expected_answer": "no, Dhaka", "expected_confidence_min": 0.5},

        # ── Absent facts (should abstain) ──
        {"question": "Does Alex have any siblings?", "expected_abstain": True, "expected_confidence_max": 0.5},
        {"question": "What is Alex's mother's name?", "expected_abstain": True, "expected_confidence_max": 0.5},
        {"question": "What car does Alex drive?", "expected_abstain": True, "expected_confidence_max": 0.5},

        # ── Time-bound / invalidated facts ──
        {"question": "Is Alex on vacation right now?", "expected_answer": "no", "expected_confidence_min": 0.5,
         "note": "Vacation to Cox's Bazar was months ago, now invalid"},
        {"question": "Does Alex have a project deadline this week?", "expected_answer": "no", "expected_confidence_min": 0.5,
         "note": "Deadline was month 1, long passed"},
        {"question": "Does Alex currently have a cold?", "expected_answer": "no", "expected_confidence_min": 0.5,
         "note": "Cold was month 1, recovered"},
        {"question": "Is Alex's wedding this month?", "expected_answer": "no, next year", "expected_confidence_min": 0.5},

        # ── Multi-session synthesis ──
        {"question": "How has Alex's career progressed over these months?",
         "expected_answer": "software engineer to senior engineer to tech lead", "expected_confidence_min": 0.5},
        {"question": "What major life changes happened to Alex?",
         "expected_answer": "moved to Dhaka, Mochi died, adopted Pixel, met and engaged Sara", "expected_confidence_min": 0.4},
        {"question": "How did Alex's pets change over time?",
         "expected_answer": "dog Mochi died, then adopted cat Pixel", "expected_confidence_min": 0.5},
    ]


# ── Fixture writing ─────────────────────────────────────────────────────────

def write_fixtures(sessions: list[dict], questions: list[dict]) -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_FILE.write_text(json.dumps({"sessions": sessions}, indent=2))
    QUESTIONS_FILE.write_text(json.dumps({"questions": questions}, indent=2))
    print(f"Wrote {len(sessions)} sessions -> {SESSIONS_FILE}")
    print(f"Wrote {len(questions)} questions -> {QUESTIONS_FILE}")


# ── HydraDB ingestion (run mode) ───────────────────────────────────────────

def run_ingestion(sessions: list[dict]) -> dict:
    """Ingest all sessions into HydraDB and return a summary dict."""
    from apps.api.pipeline.graph import run_pipeline
    from apps.api.db.hydra import HydraDB

    import os
    uri = os.environ.get("HYDRADB_URI", "neo4j://127.0.0.1:7687")
    token = os.environ.get("HYDRADB_TOKEN", "local-development-token-32-bytes")

    db = HydraDB(uri=uri, auth_token=token)
    db.connect()

    facts_stored = 0
    entities_tracked = set()
    supersessions_created = 0
    invalidations_created = 0

    print(f"\nIngesting {len(sessions)} sessions into HydraDB...\n")
    for i, session in enumerate(sessions, 1):
        result = run_pipeline(session)
        if result.get("error"):
            print(f"  [{i}/{len(sessions)}] ERROR: {result['error']}")
            continue

        write_result = result.get("write_result", {})
        facts_stored += write_result.get("facts_written", 0)
        supersessions_created += write_result.get("supersessions_applied", 0)
        invalidations_created += write_result.get("invalidations_applied", 0)

        print(f"  [{i}/{len(sessions)}] {session['session_id']} "
              f"-> {write_result.get('facts_written', 0)} facts, "
              f"{write_result.get('supersessions_applied', 0)} supers, "
              f"{write_result.get('invalidations_applied', 0)} inval")

    db.close()

    return {
        "sessions_ingested": len(sessions),
        "facts_stored": facts_stored,
        "entities_tracked": len(entities_tracked),
        "supersessions_created": supersessions_created,
        "invalidations_created": invalidations_created,
    }


def main():
    parser = argparse.ArgumentParser(description="Seed demo data for MemoryGraph")
    parser.add_argument("--run", action="store_true",
                        help="Also ingest fixtures into HydraDB")
    args = parser.parse_args()

    sessions = build_sessions()
    questions = build_questions()
    write_fixtures(sessions, questions)

    if args.run:
        try:
            summary = run_ingestion(sessions)
            print("\n" + "=" * 50)
            print("INGESTION SUMMARY")
            print("=" * 50)
            print(json.dumps(summary, indent=2))
        except Exception as e:
            print(f"\nHydraDB ingestion failed: {e}")
            print("Fixtures were still written successfully.")


if __name__ == "__main__":
    main()