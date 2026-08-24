1) This is my project and now we will build it step by step.
2) Divide this whole project into 2 weeks and then we will complete each step one by one.
3) Tell me the whole required setup configurations for this project.
4) Make models required for our database.
5) These are my models,do you think we should make any improvements in it and if yes then tell me why.
-->It gave me some good suggestions about 1-2 models,one of them were eliminating the risk of duplication.
6) Make admin so we can test.
7) Is there any mistake? or everything is working right as now we will move to next second part of the project.
--> It told me the label mistake of 'MemoryEntrys'
8) Now moving towards second part,generate lookup_profile tool.
--> It looked pretty good according to all the requirements.
9) Now we will wire our tool with actual Groq call using function calling.
-->user_id was exposed to Groq as a tool argument, meaning the LLM could potentially choose which user's data to access.
10) Remove user_id from the lookup_profile tool schema and keep only optional contact_id.Always use the trusted backend user_id when calling lookup_profile(user_id=user_id, contact_id=...)
11) build the real API endpoint, with the timeout fallback and the logging hook,this is what makes the live loop actually reachable from outside Python
-->Authentication was using username/password directly for the suggestion API and Timeout handling was too incorrect.
12) Use JWT for authentication and also replace the broad exception handling in SuggestView with Groq's groq.APIError plus json.JSONDecodeError, so genuine Groq/API or invalid-JSON failures trigger the fallback while programming errors still surface normally.
13) Build an memory agent that reads a finished conversation and extracts two separate
kinds of facts:'general_facts'(how the user personally speaks,true regardless of who
they're talking to) and 'contact_facts'(what was discussed with this specific person).
-->The agent wasn't conservative enough
14) This version will extract facts from any conversation even from a trivial
exchange,("Are you free tomorrow?" / "Yes.") doesn't deserve a permanent memory,and
the agent shouldn't store guesses, temporary details, or assumptions.
-->It strengthened the system prompt with explicit rules, including telling the model that returning an empty list is a correct answer, not a failure,otherwise models tend to invent something to fill the schema. Verified with two test cases: a rich conversation(extracted real facts) and a trivial one (correctly returned empty)
15) Switch  the fallback to 'gemini-3.5-flash-lite'
16) AI suggested wiring 'save_memory_facts()' directly into 'run_memory_agent()'. I kept them separate, because the stranger consent flow requires extracting nothing until the user decides and merging them would make that impossible without writing rows and then deleting them.
-->stranger conversations called Gemini too early
17) This version of 'EndSessionView' called 'run_memory_agent()' at the top, before checking whether the session had a contact. Two problems: a stranger's conversation was analyzed before they consented to anything, and a stranger who chose "Save" would trigger two Gemini calls for one conversation (once at end, once at save) so please look into it and change it accordingly.
-->The stranger branch now returns 'pending_decision' and exits before Gemini is touched.Extraction happens exactly once, in 'SaveAsContactView', only after the user opts in.Added two tests using 'mock_agent.assert_not_called()' to permanently guard this on both the stranger and discard paths.
18) Build endpoints to list everything learned (split into general vs per-contact) and to delete either a single entry or all memory for one contact. Every query filters by 'user=request.user', so one user can never read or delete another's memory.
-->Performed it really well.I verified it with a test that deleting all of Sara's memory leaves the user's general phrasing facts untouched,those aren't about Sara.
19) My current coverage is this,I want to increase it,add more tests.We can later add real API calling tests too but not now.
--> Coverage was increased to 87%
20) Setup frontend configuration.
--> It did setup with js,i wanted typescript
21) Scaffold the frontend: React + Vite + TypeScript, Tailwind v4, and built AuthContext, Login, and Register wired to the real backend
22) Build the real Contacts screen, loading from the API, with search and starting a session on tap or skip.
--> The 3-dot menu on each contact was opening below the visible card, clipped by a scrolling container around the list.
23) This screen is so small, when I click the 3 dots the menu opens below but I can't see it, I have to scroll down.
--> Removed the scroll constraint entirely so the card grows instead of clipping, then later re-added a taller scrollable container once I asked for the list to look nicer with a scrollbar.
24) Build "Start a new conversation" and the Delete Contact confirmation screen.
--> After deleting a contact and refreshing, I sometimes got logged out.
25) Yes it deleted, but refresh sometimes gets me back to login again.
--> Traced this to Simple JWT's default 5-minute access token lifetime, combined with the app logging the user out on any expired token instead of trying the refresh token first. Added real token-refresh logic: on an expired token, silently get a new one and retry instead of logging out.
26) Build the live Conversation screen using the Web Speech API,just get speech recognition working first, live transcript on screen.
--> TypeScript has no built-in types for the Web Speech API.
27) There are errors in the code, red lines under SpeechRecognition.
--> Wrote local type declarations for exactly what we use, since an external types package wasn't being picked up correctly.
28) Wire the transcript to real Groq suggestions, show the ranked reply cards.
--> Wanted a way to edit a suggested reply or type one from scratch, not only pick from the 3 as-is.
29) I want the user to edit the reply or type their own, and one tap on a reply should speak it immediately, not need an extra step.
--> Rebuilt the cards,tapping speaks immediately, a separate pencil icon edits first, plus a free-type box. Added an is_custom flag to SelectSuggestionView so an edited/typed reply is accepted, not only an exact match.
30) Started seeing suggestions fall back to generic replies more than real AI replies.
--> The model was intermittently hallucinating a fake tool call (once literally inventing one named "json") instead of answering.
31) Why is it doing this when we never built a tool called that? Can we fix the actual root cause, not just work around it?
--> Traced this to how this model's internal format gets translated through the standard API when tool-calling and JSON output are both requested in one call. Applied Groq's own recommended fix,retried once at a lower temperature.
32) I want the last several messages of the conversation remembered, so replies make sense across turns, not just react to one line.
--> Made the hallucination issue noticeably worse, and the frontend started aborting requests that were still genuinely in progress.
33) Isn't 4 messages too few to remember? Should we increase it?
--> Tested 4 vs 6 vs 10 messages of history directly, comparing real failure rates each time. Settled on 6 as the best tradeoff, and increased the client timeout to match.
34) Can't we just take Groq's plain text and convert it to JSON ourselves, instead of asking it for JSON directly?
--> Helped, but a related version of the same confusion could still happen.
35) Rebuild the suggestion agent into two separate calls,one only decides whether to look up saved facts, a second only generates the reply.
--> This was the real fix: splitting the two concerns means tool-calling and "return JSON" instructions are never in the same request, removing the actual condition causing the confusion.
36) Can't we just use one API call instead of two, to save cost and latency?
--> Tried it,always deterministically fetch the contact's profile in Python instead of letting the model decide.
37) No, I don't want this, give me the 2 API call version back.
--> Reverted on my own,a single call removes the only place in the whole project where the model genuinely, agentically decides whether to call a tool.
38) Add a safe default per Ayesha's suggestion.
--> If the decision call fails outright, the request now proceeds without personalization instead of failing entirely.
39) Why is it giving me only 1 or 2 replies sometimes instead of always 3?
--> The prompt never explicitly said how many replies to produce.
40) Please fix this so it's always exactly 3.
--> Added an explicit instruction, a length constraint in the schema, and a hard backend guard that falls back if fewer than 3 ever come back.
41) Why is memory about ME being written under a specific CONTACT's profile instead of my own?
--> The instructions for "general fact" vs "contact fact" were too vague, letting the model file things about me under whichever contact happened to be in the room.
42) Please fix this....Fatima's memory should only contain facts about Fatima.
--> Sharpened the prompt with a concrete test the model can apply: would this still be true talking to someone completely different?
43) Why is it storing the same fact twice, worded slightly differently, after a second conversation?
--> The memory agent had no way of knowing what it had already saved.
44) Please stop it from storing repetitive memory.
--> Passed the already known facts into the prompt and told it explicitly not to re-extract anything already covered, even reworded.
45) Wire End Conversation to the backend, build the Save/Discard screen for strangers.
--> Ending with a known contact felt very slow, with the button just frozen.
46) The end conversation button is very slow, and replies also sound very robotic, make them more natural.
--> Moved the wait onto the Summary screen instead of freezing the button. Separately, rewrote the reply prompt with a concrete good/bad example to push toward short, casual, spoken phrasing.
47) Build the Memory Viewer, scope a contact's 3-dot menu to only their memory, and show a summary of what was learned after ending a conversation.
--> The unscoped "view all memory" route rendered a blank white page.
48) When I press "view all memory" it goes completely blank.
--> The bare /memory route wasn't defined alongside the new scoped one. Fixed the routing and added a fallback redirect so an unmatched URL can never render blank again.
49) I want a "delete everything" option for my own memory too, "you" instead of "user", and a contact's memory should use their real name instead of "Partner".
--> Traced "Partner" to the literal transcript text handed to Gemini, which labeled every line that way, not something Gemini invented.
50) Please fix all three.
--> Added a GeneralMemoryDeleteView endpoint, and fixed the transcript-builder to use the contact's real name (or "the other person" for a stranger).
51) Add an inactivity timer: warn after a few minutes of no activity, auto end if untapped.
--> Typed replies weren't resetting the timer, only speech was.
--> Restored the missing timer-reset call in the typed-reply function.
52) Add ruff for backend linting, get a clean pass.
--> A few real issues: an unused variable, an ambiguous single-letter name, imports not grouped at the top.
53) Please fix what ruff found.
--> Fixed all of it, then ran ruff's auto-formatter across the backend as its own separate commit.
54) Fix the ESLint errors too.
--> Several real frontend issues: a function changing identity every render, effects calling setState synchronously.
55) I genuinely don't want to do this, leave it as is.
--> Left it,a deliberate, informed decision, not a default.
56) I did the audit of my repo,these are my issues,let's correct them one by one but first tell me which are more problematic.
--> Serious issues: the Django SECRET_KEY (which also signs every login token) was hardcoded and committed to git, DEBUG was hardcoded True, requirements.txt was a dump of my whole computer's packages including Windows-only ones that couldn't even install elsewhere, and tapping a reply after a failed request silently did nothing.
57) Please fix everything the audit found.
--> Fixed all of it,secrets moved to environment variables, requirements.txt regenerated clean, and the reply-tap flow now always speaks the text regardless of whether logging it succeeded.
58) I ran a second, independent audit to double check.
--> More real things: a null transcript crashed the suggestion endpoint, Django REST Framework wasn't actually registered as an installed app, the memory agent's AI output was never shape-checked the way the suggestion agent's was.
59) Please fix all of these too.
--> Fixed all four, and added a test for the one crash path that had zero coverage.
60) Write a proper README,the original was four lines with no real setup instructions, which both audits flagged.
--> First draft included a "Known Limitations" section.
61) Remove that, and make sure everything a README should have is present.
--> Reframed it as forward-looking "Future Improvements" instead of removing it outright, and added a proper Usage section and full API reference.
62) Build a comprehensive test suite — unit, integration, and at least one real end-to-end test, clearly labeled.
--> Tests existed but weren't organized into those three tiers, and had no true end-to-end test chaining multiple real endpoints together.
63) Please organize and complete this properly.
--> Reorganized into three labeled sections, and added two full end-to-end tests chaining register → contact → session → suggest → select → end → memory in one continuous flow.
64) Add a separate set of tests that genuinely call the real Groq and Gemini APIs, not mocked.
--> None existed yet for this yet.
65) Let's run the live API tests.
--> Ran them for real,all passed, and genuinely hit a live Gemini rate-limit error mid-run that correctly triggered the fallback model, real proof the safety net works under real conditions, not just in theory.
66) Update README