# RV News SharePoint publishing flow, continuation handoff

## Purpose

Finish and test the internal-only SharePoint publish action for the RV Industry
News page. This document records the live state as of 12 August 2026, so the
next session can continue without re-discovering the setup.

No launch communication, SharePoint page publication, navigation change, or
colleague notification is authorised as part of this work.

## Live environment

- SharePoint site: `https://thetfordeu.sharepoint.com/sites/ProductManagementEurope`
- List: `RV News Queue`
- Review view currently open in SharePoint: `Editorial Review`
- Power Automate environment: `Thetford Europe (default)`
- Flow name: `Publish RV News edition`
- Flow ID: `b0a8a273-a536-4cd4-a348-760a4e601ab7`
- Flow details URL:
  `https://make.powerautomate.com/environments/Default-2a66a3e7-98dd-49f4-9d30-0435daf1ab00/flows/b0a8a273-a536-4cd4-a348-760a4e601ab7/details`
- Owner connection: `dvandenberg@thetford.eu` using SharePoint.

The saved flow is shown as **On**, type **Instant**, created 12 August 2026 at
10:45, and has no run history.

## Current list and landing-page state

- The RV Industry News landing page already shows image-based cards with left
  aligned content, coloured category labels, wrapped titles, a clickable title,
  and a visible article link.
- `Article URL` is plain text and is used by the card formatting.
- The list includes the intended editorial values: `Review`, `Review - image
  issue`, `Selected`, `Rejected`, and `Published`.
- `Article ID` is configured to prevent duplicate records.
- The Current Edition view/card formatting is in place. Do not alter it while
  repairing the flow.

## Continuation update, 13 August 2026

The publish flow has now been repaired and successfully tested.

- The trigger and the current-edition query now use the actual `RV News Queue`
  list selected from SharePoint's drop-down, not custom typed values.
- Flow checker: **0 errors, 0 warnings**.
- The flow appears under list **More > Integrate > Flows > Publish RV News
  edition** when a list item is selected.
- Test run: 13 August 2026, duration 3 seconds, **Succeeded**.
- The two test records are now `Published` and `Current edition = Yes`.
- No SharePoint page was published and no notification was sent.

The unresolved item is the landing-page list web part. It uses the `Week 32
cards` view, view ID `8b2f316a-d26f-46f6-bfa4-00180b254e26`, which still
renders the static Week 32 cards. The target cards do not appear there.

Useful known identifiers for resolving that final issue:

- List ID: `e1a3f869-5d3b-4355-ac26-a0b7f7edc735`
- Landing page: `https://thetfordeu.sharepoint.com/sites/ProductManagementEurope/SitePages/RV-Industry-News.aspx`
- The classic view editor is reachable at:
  `https://thetfordeu.sharepoint.com/sites/ProductManagementEurope/_layouts/15/ViewEdit.aspx?List=%7Be1a3f869-5d3b-4355-ac26-a0b7f7edc735%7D&View=%7B8b2f316a-d26f-46f6-bfa4-00180b254e26%7D`

The legacy view editor allowed `Current edition is equal to Yes` to be entered,
but saving returned a SharePoint `View does not exist` error and the live view
remained unchanged. Applying the modern URL filter
`FilterField1=Currentedition&FilterValue1=Yes` also showed an empty list even
though the test records visibly show `Current edition = Yes` in the normal list.
Do not claim the landing page is automated until this discrepancy is resolved.

## Test data, intentionally preserved

Two cards are prepared for the first publishing test. Both are in edition
`2026-W32-test`, have images, and have been set to `Selected`:

| List ID | Title | Status | Current edition |
|---:|---|---|---|
| 6 | Eifelland tests the practical limits of an electric campervan | Selected | No |
| 7 | Flowcamper shows the Max Autark Grande | Selected | No |

No flow run has been made. The existing current edition has therefore not been
changed by the test preparation.

## What failed, and why

1. `Publish RV News edition` did not appear under SharePoint list
   **Integrate > Flows**. Only `Request sign-off` appeared.
2. The trigger's `List Name` had originally been typed as a **custom value**.
   It must instead be selected from the SharePoint list drop-down as
   `RV News Queue`, otherwise SharePoint does not register the flow against the
   list.
3. In the Power Automate editor, after correcting the trigger, Power Automate
   reported: `Your flow should contain at least one trigger and one action.`
4. The editor canvas showed only `For a selected item`. The actions thought to
   have been configured earlier had not persisted into the saved definition.
5. A partial, unsaved rebuild was started in the editor. It contains:
   - `For a selected item`, correctly bound to the real `RV News Queue` list.
   - `Get item`, correctly bound to the same site/list, with the selected item
     ID dynamic value.
   - A partially configured `Get items` action, which is not yet valid.

Do **not** save this partial editor version. It is not a working publish flow.
The original saved flow is also incomplete, so rebuilding it deliberately is the
right approach.

## Required final behaviour

Run the flow from a selected list item, using the selected item's `Edition` as
the edition to publish. It must:

1. Read the selected item and obtain its edition.
2. Find all list records where:
   - `Edition` equals that edition, and
   - `Status` equals `Selected`.
3. Stop without changing anything if that query returns zero records.
4. Validate that every candidate has a non-empty `Article URL` and an article
   image. If not, stop without altering the current edition.
5. Clear `Current edition` on the prior current-edition records.
6. Mark every selected card in the chosen edition as:
   - `Status` = `Published`
   - `Current edition` = `Yes`
7. Leave all rejected, review, historical, and non-selected records untouched.
8. Do not publish the SharePoint page and do not send Teams, email, or site
   notifications.

Fewer than 8 cards is permitted. Dennis explicitly decided that a small weekly
edition is still worth publishing if news is limited.

## Recommended rebuild route

Start from the saved flow's details page, choose **Edit**, then rebuild in this
order. Use real SharePoint drop-down selections, never custom typed list values.

1. **Trigger: For a selected item**
   - Site Address: `Product Management OEM Europe - https://thetfordeu.sharepoint.com/sites/ProductManagementEurope`
   - List Name: select `RV News Queue`.

2. **Get item**
   - Same site and list.
   - ID: dynamic `ID` from `For a selected item`.

3. **Get items: selected cards for the edition**
   - Same site and list.
   - Use an OData filter generated from the preceding `Get item` output:
     `Edition eq '<selected item Edition>' and Status eq 'Selected'`.
   - Use the expression builder or dynamic-content tokens, not a manually typed
     custom list value.

4. **Condition: candidates returned?**
   - Check that the selected-cards query has one or more rows.
   - No branch: terminate as succeeded, with no updates.
   - Yes branch: continue.

5. **Validate candidates**
   - Use a Filter array or an Apply to each condition to identify empty
     `Article URL` or missing `Article image` values.
   - If any exception exists, terminate without touching the current edition.

6. **Get items: existing current edition**
   - Same site/list.
   - Filter: `Current edition` equals Yes.

7. **Apply to each: clear prior current edition**
   - Update each returned item: `Current edition` = No.
   - Do not alter its status.

8. **Apply to each: publish the selected cards**
   - For every record from step 3, update:
     - `Status` = Published
     - `Current edition` = Yes

9. Save, use **Flow checker**, then return to the SharePoint list and verify:
   **Integrate > Flows > Publish RV News edition** is visible.

10. Test using one of the two `2026-W32-test` rows. Afterwards verify:
   - both test rows are Published and Current edition = Yes;
   - prior current-edition rows are no longer current;
   - the RV Industry News landing-page cards now show the test edition;
   - no SharePoint page, navigation, or notification was changed.

## Important safety notes

- Do not clear the existing current edition before the selected-card query and
  validation both succeed.
- Do not use a count guard requiring 8 to 12 cards. Fewer cards are valid.
- Do not replace or delete the two prepared test cards.
- Do not use the old GitHub dashboard as a publication source for these cards.
  The SharePoint queue and its images are now the source for the SharePoint
  landing page.
- The weekly intake flow is separate from this task. Do not change it while
  completing the publish flow.

## Related local documentation

- `automation/POWER_AUTOMATE_BUILD.md` describes the intended no-AI weekly
  intake and the original publish-flow requirements.
- This handoff supersedes its publish-flow section only where it records the
  observed live state and adds the zero-candidate safety condition.
