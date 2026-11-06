# Sanity check: answers with cited article URLs

Captured 2026-11-06 against the live store `fileSearchStores/supportarticles-7p0xuqudsdq3`
(398 documents, 942 estimated chunks), model `gemini-3.6-flash`, system prompt verbatim from
`prompts/system_prompt.txt`, using `python -m kbsync.ask "<question>"` (File Search tool).
Output below is copied unedited from the terminal.

## "How do I add a YouTube video?"
```
To add a YouTube video to your OptiSigns account, follow these steps:

* Go to **Files/Assets** in the OptiSigns portal and select **Apps**.
* Search for and select the **YouTube** app.
* Enter a **Name** for your asset and paste the link to your video in the **URL** field.
* (Optional) Adjust any display options (e.g., **Mute**, **Caption**) or playback options (**Start At**, **End At**).
* Click **Save**, then assign the created YouTube app asset to your screen, playlist, or schedule.

Article URL: https://support.optisigns.com/hc/en-us/articles/360051014713-How-to-Use-YouTube-with-OptiSigns
```

## "How do I change a user's role in my team?"
```
To change a user's role in your team, follow these steps:

* Go to your **Profile** and select **Account Members** (or navigate to **Manage Members**).
* Find the team member whose role you want to change.
* Click the **...** (three dots) icon next to the member's name.
* Select **Change Role**.
* Choose the new role from the drop-down menu and save your changes.

Article URL: https://support.optisigns.com/hc/en-us/articles/360034883113-Working-with-Teams-and-Security-Levels
Article URL: https://support.optisigns.com/hc/en-us/articles/360046356113-Advanced-Security-Managing-User-Roles
```

## "What is the capital of France?" (out of scope)
```
I am OptiBot, the customer-support bot for OptiSigns.com. I can only answer questions based on the provided OptiSigns documentation, so I do not have information regarding the capital of France.

Please let me know if you have any questions about OptiSigns!
```

## What this shows
- At most 5 bullets and at most 3 `Article URL:` lines, as the system prompt requires.
- In all three runs the model wrote the `Article URL:` lines itself; the CLI's fallback that appends URLs from retrieval metadata was not needed.
- Out-of-scope questions are refused instead of answered from general knowledge.
- This is a CLI run, not an AI Studio / Playground session: the OpenAI Assistants Playground the brief refers to no longer exists, and AI Studio's chat does not document attaching a File Search store.
