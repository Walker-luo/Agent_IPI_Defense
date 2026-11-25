# BaseIntent 执行路径示意图生成提示词

内置 ImageGen 生成。首轮参考图为 GrantBind 的 `fig/architecture/AI_generate/4_chatgpt.png`，用于构图、配色和图标风格。第二轮和第三轮分别以上一轮生成图为输入，修正并精简标签。

## 首轮生成

```text
Create a new flat 2D BaseIntent architecture figure for a two-column IEEE/ACM security systems paper. Image 1 is the GrantBind visual reference. Borrow its wide landscape composition (aim for approximately 2.6:1), three softly tinted regions, small consistent navy line icons, rounded module tiles, and compact paper typography. Use warm ivory on the left for task and planning, pale ice blue in the center for enforcement and evidence, and pale mint on the right for execution and reply. Use navy for the main path and blue for the read exemption, with teal for evidence and feedback. Center the composition and keep outer margins equal. Text should be larger than the icons and readable at paper width. The BaseIntent diagram below is the sole source of module names and directions.

LAYOUT AND CONNECTIONS
- Upper left: a “Trusted task” tile with a request icon points right to “L2 Authorization” with a compact key icon. Inside the authorization tile show the three listed sublabels in order, with the host step between the two calls. A short navy arrow points down from it into “Planner”.
- The middle row has exactly five aligned tiles in this order: “Planner” (robot), “L2 Batch Precheck” (checklist), “L3 Action Audit” (magnifier), “Reference Monitor” (lock), “Native Tools” (tool icon). Every adjacent tile is connected by one rightward navy arrow. The arrow from Monitor to Native Tools is labeled “One-use tickets”. In the precheck tile put “Grants and native schema”. Below the audit title put “Intent, constraints, evidence”. The monitor tile includes “Whole-batch receipt”. In the tools tile put “Original batch order”.
- A distinct blue orthogonal bypass labeled “Eligible reads skip L3” starts at the top edge of L2 Batch Precheck, crosses above L3, and bends down with its only arrowhead entering the top edge of Reference Monitor. Leave a visible gap between this bypass and the L3 tile. Non-exempt calls travel along the middle row through L3. Both paths reach the Monitor before any execution.
- Align a lower row of four smaller tiles in this order: “L1 Planning View” below Planner, “Raw History” below L3, “Intent Progress” below Monitor, and “Final Reply or Clarification” below Native Tools. From Native Tools, a teal line labeled “Tool results” runs down, left, and into the upper right side of Raw History, with its arrowhead at Raw History. Raw History points to three destinations: left into L1 Planning View, vertically up into the bottom of L3 (label “Evidence”), and right into Intent Progress (label “Matched execution evidence”). L1 Planning View points vertically up into the bottom of Planner. Keep the tool-return route and evidence route on different lanes with no intersections.
- Intent Progress points right into Final Reply or Clarification. A separate dashed teal feedback path leaves the bottom edge of Intent Progress, runs left below all lower tiles, then up around the left edge of the lower row and into the left side of Planner. Label it “Current or next intent”. Keep this dashed feedback path unmistakably separate from L1 and the main execution row.

图中所有可见文字只能使用以下内容（只渲染引号里的英文文字，每项一次，可按需换行）：
“Trusted task”
“L2 Authorization”
“Call 1: Intents and goal types”
“Host: Fold prep and assign IDs”
“Call 2: Global grants and progress links”
“Planner”
“L2 Batch Precheck”
“Grants and native schema”
“L3 Action Audit”
“Intent, constraints, evidence”
“Reference Monitor”
“Whole-batch receipt”
“One-use tickets”
“Native Tools”
“Original batch order”
“Eligible reads skip L3”
“L1 Planning View”
“Raw History”
“Intent Progress”
“Final Reply or Clarification”
“Tool results”
“Evidence”
“Matched execution evidence”
“Current or next intent”

Section names in this prompt are layout instructions. Keep the three regions unlabelled. Avoid extra titles, legends, arrows, layers, attacker tiles, untrusted-input tiles, background gradients, drop shadows, branding, and decorative objects. Give every connector one obvious arrowhead at its sole destination. If space is tight, shrink icons and increase the lower routing space so all labels and edges remain clear.
```

## 第二轮修订

```text
Refine the supplied BaseIntent architecture image. Preserve the current wide three-region composition, every tile and icon, the layouts and directions of all arrows, and every other label. Make only these two typography corrections:
1. In the bottom sublabel inside the top left L2 Authorization tile, replace the existing text with the exact label “Call 2: Global grants and progress links”. Make the numeral 2 solid dark navy and as legible as the numeral 1 above it. Two lines are fine.
2. Above the teal rightward arrow from Raw History to Intent Progress, replace “Matched execution evidence” with the exact label “Raw messages”. Keep the teal arrow running right from Raw History into Intent Progress.
Retain the same three pastel zone backgrounds and white outer margin. Keep the bypass from L2 Batch Precheck to Reference Monitor and the dashed progress feedback to Planner intact. No other changes or extra text.
```

## 第三轮精简

```text
Edit the supplied clean BaseIntent PNG for readability at paper width. Preserve the three pastel regions, exact module positions, every icon, all node labels, and every arrow and its direction. Limit the edits to the labels below.

Inside L2 Authorization use three equal-height stripes with one dark navy line each. Use the exact text “1. Intents and goal types”, “Host: Fold prep, assign IDs”, and “2. Grants and progress links”. Use bold, fully opaque numerals. Center them and keep them at the same font size. Maintain padding inside the stripes.

Inside the L3 Action Audit tile replace the small bottom subtitle “Intent, constraints, evidence” with “Task alignment” on one line. Center the subtitle and leave the teal upward Evidence arrow in place.

Above the rightward line from Reference Monitor to Native Tools replace the two-line label “One-use tickets” with the one-line label “Tickets”. Center it over that connector; give it visible clearance from the arrow and neighboring tiles. Keep the arrow pointing solely into Native Tools.

Preserve the green label “Raw messages”, the blue bypass arrow entering Reference Monitor, and the dashed feedback arrow entering Planner. Keep all other details identical. No red markup, added text, new graphics, or moved boxes.
```
