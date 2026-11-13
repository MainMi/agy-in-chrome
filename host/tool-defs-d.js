// Tool schema entries, split out of tool-definitions.js — pure
// refactor, behavior unchanged.
import { z } from "zod";

export const TOOLS_D = [
  {
    name: "upload_image",
    description:
      "Upload a previously captured screenshot (from the computer tool's screenshot action) to a file input. Identify the target with `ref` from read_page or find; the target must be an <input type=\"file\"> (especially useful for hidden inputs).",
    paramShape: {
      imageId: z
        .string()
        .describe(
          "ID of a previously captured screenshot (from the computer tool's screenshot action) or a user-uploaded image"
        ),
      tabId: z
        .number()
        .describe(
          "Tab ID where the target element is located. This is where the image will be uploaded to."
        ),
      ref: z
        .string()
        .describe(
          'Element reference ID of the file input from read_page or find tools (e.g., "ref_1", "ref_2").'
        ),
      filename: z
        .string()
        .optional()
        .describe(
          'Optional filename for the uploaded file (default: "image.png")'
        )
    }
  },
  {
    name: "retranscribe_recording",
    description:
      "Re-run transcription for a saved recording whose transcript failed at stop (e.g. a transient OpenAI error). Re-assembles the durable audio segments, re-transcribes them, and patches trace.json on disk, overwriting the previous transcript. Returns the updated transcript status and utterance count. Constraints: only works for the MOST RECENT recording recorded after this feature shipped (a newer recording clears the in-browser audio store; older sessions lack the segment anchors needed to map timestamps). Only call it to recover a recording whose transcript actually failed — re-running on a good one replaces the transcript with a fresh result and could worsen it if OpenAI is currently failing.",
    paramShape: {
      recording_id: z
        .string()
        .describe(
          "The recording_id shown in the bundle path after a recording_complete notification (e.g. the timestamp-based id)."
        )
    }
  },
  {
    name: "file_upload",
    description:
      "Upload one or more local files (by absolute path) to a file input element on the page. Use read_page or find to locate the <input type=\"file\">, then pass its ref — do not click file inputs, which opens a native picker you cannot see. Each file must already exist on this machine (the same machine as the browser); the real path is passed straight to the browser, no staging. Keep the combined size of all files in a single call under ~10 MB.",
    paramShape: {
      paths: z
        .array(z.string())
        .describe(
          "Absolute paths to the files to upload (e.g., ['/home/user/report.pdf']). Each file must already exist on this machine."
        ),
      ref: z
        .string()
        .describe(
          'Element reference ID of the file input from read_page or find tools (e.g., "ref_1", "ref_2").'
        ),
      tabId: z
        .number()
        .describe(
          "Tab ID where the file input is located. Must be a tab in the current group. Use tabs_context_mcp first if you don't have a valid tab ID."
        )
    }
  }
];
