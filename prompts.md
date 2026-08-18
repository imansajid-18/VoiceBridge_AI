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
