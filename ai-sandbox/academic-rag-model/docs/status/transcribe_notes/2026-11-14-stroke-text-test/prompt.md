# Prompt for Gemini: transcribe handwriting from stroke coordinates

Do not open any other file in this repository, and do not look for images of this
handwriting. The point of the test is to read the strokes themselves.

Read this file and nothing else: `ai-sandbox/academic-rag-model/docs/status/transcribe_notes/2026-11-14-stroke-text-test/s1.txt`

It holds handwriting from a university lecture note, saved as pen strokes:
- One stroke per line, in the order they were drawn: `<n>: x,y x,y x,y ...`
- Each stroke is a simplified polyline of pen positions in pixels. The origin is the
  top-left corner of the whole handwriting; x grows to the right and y grows downward.
- Letters are roughly 30 to 50 px tall. Gaps between strokes show word and line breaks.
- A long near-horizontal stroke is probably an underline or a rule.

Task:
1. Say first whether you think you can transcribe handwriting from raw coordinates, and
   what your method is (for example, mentally plotting each stroke, or grouping strokes
   into characters).
2. Group the strokes into lines of text, then characters or words. List the stroke
   numbers you assign to each line.
3. Transcribe the text, line by line. Use LaTeX for any mathematics. Mark any word you
   are unsure of with [?]. Do not invent text you cannot support from the strokes.
4. Give a confidence from 0 to 1 for each line, and say what the confidence rests on.

Output the transcription and your line groupings in the reply. Do not create files.
