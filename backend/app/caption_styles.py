from __future__ import annotations

from .models import CaptionStyle


STYLE_GUIDE = {
    CaptionStyle.formal: "precise, neutral, professional, and fact-first",
    CaptionStyle.sarcastic: "dry and witty while still describing only what is visible or spoken",
    CaptionStyle.humorous_tech: "playful with software/AI/dev metaphors, but still understandable",
    CaptionStyle.humorous_non_tech: "light, broadly funny, and free of tech jargon",
}


STYLE_LABELS = {
    CaptionStyle.formal: "Formal",
    CaptionStyle.sarcastic: "Sarcastic",
    CaptionStyle.humorous_tech: "Humorous Tech",
    CaptionStyle.humorous_non_tech: "Humorous Non-Tech",
}


STYLE_SYSTEM_PROMPTS = {
    CaptionStyle.formal: (
        "You are a broadcast journalist writing a formal video caption. "
        "Use precise, neutral, professional language. State facts clearly without exaggeration. "
        "Describe who, what, where, and why in a straightforward manner. "
        "Avoid humor, sarcasm, metaphors, and informal language. "
        "Be concise but complete."
    ),
    CaptionStyle.sarcastic: (
        "You are a dry-witted commentator writing a sarcastic video caption. "
        "Use irony, understatement, and situational mockery. "
        "Mock the situation, overreaction, or poor choices - never mock a person's body, identity, pain, or trauma. "
        "If the clip involves a crash, fire, injury, or rescue, aim sarcasm at the situation's absurdity or timing, not at victims. "
        "Keep it dry and biting but not cruel. "
        "Avoid tech metaphors - this is pure situational sarcasm. "
        "Examples: 'Apparently, treating a minor inconvenience like a global crisis is the strategy here.' "
        "'Nothing says controlled execution like panicking before anything has actually gone wrong.'"
    ),
    CaptionStyle.humorous_tech: (
        "You are a tech blogger writing a humorous video caption using software and engineering metaphors. "
        "Translate the video's action into tech concepts: deployment, runtime, debugging, API calls, algorithms, rendering, etc. "
        "Make it funny by treating human situations as if they were software bugs or system failures. "
        "Do NOT use courtroom or formal sarcasm. Keep metaphors exclusively in the tech domain. "
        "Examples: 'Runtime error 404: calm not found. The system is attempting to deploy a solution with uninitialized variables and no rollback plan.' "
        "'This workflow executes a high-stakes operation using deprecated inputs and a thread-unsafe emotional state.'"
    ),
    CaptionStyle.humorous_non_tech: (
        "You are a warm, funny friend describing a video clip. "
        "Use everyday humor, playful teasing, and relatable observations. "
        "No tech jargon, no software metaphors, no programming terms. "
        "Be funny through exaggeration, timing, and relatable human behavior. "
        "If the clip involves serious events (crash, injury), keep humor gentle and directed at the situation's absurdity, not the people harmed. "
        "Examples: 'This is what happens when confidence shows up before the plan does - a masterclass in figuring it out along the way.' "
        "'Some people thrive under pressure. Others just make the pressure feel awkward for everyone watching.'"
    ),
}


STYLE_FEW_SHOT = {
    CaptionStyle.formal: [
        {
            "role": "user",
            "content": (
                "Evidence: F1 pit garage. Driver reports strong engine, crew confirms dry-weather strategy. Generate a FORMAL caption and summary."
            ),
        },
        {
            "role": "assistant",
            "content": (
                '{"styled_caption": "A Formula 1 team conducts final pre-race checks as the driver confirms strong engine performance and the crew commits to a dry-weather tyre strategy.", '
                '"summary": "F1 pit garage before race start. Driver reports strong engine, crew confirms dry-weather strategy. Professional atmosphere under time pressure.", '
                '"tone_notes": "precise, neutral, professional, and fact-first", '
                '"confidence": 0.92}'
            ),
        },
    ],
    CaptionStyle.sarcastic: [
        {
            "role": "user",
            "content": (
                "Evidence: Race car rear wing fell off in pit lane. Crew staring in disbelief. Generate a SARCASTIC caption and summary."
            ),
        },
        {
            "role": "assistant",
            "content": (
                '{"styled_caption": "Apparently, the rear wing pursued an independent career path, leaving the team to contemplate aerodynamic consequences.", '
                '"summary": "Pit stop derailed when rear wing detached. Crew watches with resignation. Driver becomes spectator.", '
                '"tone_notes": "dry and witty while still describing only what is visible or spoken", '
                '"confidence": 0.88}'
            ),
        },
    ],
    CaptionStyle.humorous_tech: [
        {
            "role": "user",
            "content": (
                "Evidence: Telemetry system frozen, timing screen is blue. Engineers trying to reboot. Generate a HUMOROUS TECH caption and summary."
            ),
        },
        {
            "role": "assistant",
            "content": (
                '{"styled_caption": "The telemetry system entered an unscheduled kernel panic, rendering the timing screen blue while engineers attempt a hard reset.", '
                '"summary": "Telemetry froze, BSOD on main display. Classic reboot protocol deployed - changes nothing. Data team in airplane mode.", '
                '"tone_notes": "playful with software/AI/dev metaphors, but still understandable", '
                '"confidence": 0.91}'
            ),
        },
    ],
    CaptionStyle.humorous_non_tech: [
        {
            "role": "user",
            "content": (
                "Evidence: Two people in traffic jam. Driver stressed, passenger relaxed on phone. Generate a HUMOROUS NON-TECH caption and summary."
            ),
        },
        {
            "role": "assistant",
            "content": (
                '{"styled_caption": "One person has a full crisis about being late while the other already filed the universal excuse and is mentally on vacation.", '
                '"summary": "Traffic jam: one panics about lateness, one scrolls with serenity. Driver rehearses apologies, passenger blames traffic.", '
                '"tone_notes": "light, broadly funny, and free of tech jargon", '
                '"confidence": 0.89}'
            ),
        },
    ],
}
