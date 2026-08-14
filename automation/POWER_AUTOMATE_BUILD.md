# RV News private review flow, no-AI fallback

Create this as a cloud flow in the Product Management Europe environment. Use
the owner connection only. Do not publish the RV Industry News page, change site
permissions, add navigation, or notify anybody except Dennis in the final Teams
action.

## 1. Trigger and input

1. Create a private document library named `RV News Automation` in the existing
   Product Management Europe site. Hide it from navigation.
2. Create an `Incoming` folder in that library and sync it to the work laptop.
3. Create an automated cloud flow triggered when `Incoming/<edition>/manifest.json`
   is created. Add an explicit path condition so the flow ignores all image files.
4. Get the file content, parse the JSON and process only manifests whose
   `status` is `ready_for_raw_review`.

## 2. Raw review items

This fallback deliberately uses no AI Builder or generative-AI capability. The
staging script supplies at most twelve image-complete candidates, each clearly
marked for editorial review. For each manifest candidate, create an item in
`RV News Queue` with:

| Queue field | Manifest or AI value |
|---|---|
| Title | `title` |
| Status | `Review` |
| Category | `Unclassified` |
| Summary | `summary` |
| Why it matters | `Editorial review required before publishing.` |
| Source | `source` |
| Article URL | `article_url` |
| Article ID | `article_id` |
| Collected date | `published` |
| Edition | `edition` |
| Current edition | `No` |

`Article ID` is configured in SharePoint to enforce unique values. This blocks a
second queue record for the same source article, even if a manifest is uploaded
again. A later flow refinement can turn that blocked duplicate into a clean
"skipped" branch in the run history.
Use the image file from the same manifest folder to populate the list's native
`Article image` field. If that upload fails, set Status to `Review - image issue`
and exclude it from publication.

## 3. Private notification

After all items are created, send one Teams chat to Dennis only. It links to the
`Editorial Review` view filtered to the manifest edition and includes the number
of created cards and image exceptions. No channel message, SharePoint news post,
site email or page publication is allowed.

## 4. Publish edition button

Create an instant cloud flow for the `RV News Queue` list called `Publish RV News edition`.

1. Accept the selected list items and require 8 to 12 items, all with Status
   `Selected`, a non-empty Article URL and a native Article image.
2. Reject a mixed-edition selection.
3. Set `Current edition` to `No` for the current published items.
4. Set the selected items to Status `Published` and `Current edition` `Yes`.
5. Do not publish the SharePoint page or send any notification.

## 5. Required list configuration

Create the following fields in `RV News Queue`:

- `Status`, choice: Review, Review - image issue, Selected, Rejected, Published
- Add `Unclassified` to the existing `Category` choice field for the no-AI review queue.
- `Article URL`, single line of text
- `Article ID`, single line of text, indexed and unique where supported
- `Collected date`, date only
- `Edition`, single line of text, indexed
- `Current edition`, yes/no, default No

Create two gallery views:

- `Editorial Review`: Status is Review, sorted Edition descending then Collected date descending.
- `Current Edition cards`: Current edition is Yes, sorted Collected date descending. Embed this view in RV Industry News.

The card JSON must use the plain text `Article URL` field for both the title's
`href` and a visible `Read article` link. This avoids the incompatible hyperlink
field used in the first prototype.
