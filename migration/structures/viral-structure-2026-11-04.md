# Viral structure mining, 2026-11-04 (Inteligência Viva, owner order 2026-11-04)

Owner, 2026-11-04: "Existe uma estrutura viral... tem que ser mapeada perfeitamente". This page maps what could be
measured, says what could not, and turns it into production specs. Evidence JSON: `../evidence/vidiq/2026-11-04/`
(`breakout-sample.json`, `structure-maps.json`, `weak-contrasts.json`, `case-studies.json`, `synthesis-counts.json`).
Spending: 125 vidIQ credits (3,069 -> 2,944; 140 of the 150/day cap with the 15 earlier today; ledger updated).
Everything else was free (WebSearch/WebFetch, public thumbnails). No manifold, no new generation.

Labels: **MEASURED** = read from vidIQ/YouTube metadata or a transcript today; **VIDIQ_MODEL** = vidIQ's outlier
score; **ESTIMATE** = our arithmetic; **INFERRED** = a reading we could not confirm; **NOT_MEASURED** = not observable
from outside (CTR, retention, impressions, cut rate from a transcript).

## 0. Verdict (what the evidence says, including what it does not)

1. No "monetized in 7-10 days" case could be verified. Every one found is a course or lead-magnet seller; the one with
   numbers (basketball Shorts) used a **5-year-old account**, and the 7-day claim does not match its own transcript.
   The official routes are unchanged: 1,000 subs + 4,000 public long hours, or 1,000 subs + 10M public Shorts views in
   90 days (Shorts-feed watch time does not count toward the 4,000 h).
2. Inside a video, the "viral structure" is real but **is not what separates winners from weak** in this niche: 3 of 6
   Bible long winners have no hook at all (calm opening, or a slideshow with one plain sentence per 25 s) and still
   reached 35K-397K views. What the winners share is the **package and the length**: a "Full Story"/question title (5/6),
   a face-and-name thumbnail (6/6), 13-28 min (6/6). The weak videos have label titles (6/7) and are mostly 4-7 min
   (5/7 under 10 min). Structure then decides retention and the next view (hours per view), which we cannot see for
   other channels.
3. The earlier internal finding stands and sharpens ("none of 11 structure attributes separates winners from weak; next
   test is the package"): the next change is the package and length, then the opening.
4. Shorts route (10M views / 90 days) is out of reach by 2026-12-01: see section 6. The long-hours route is only reachable
   through one breakout long or a long compilation that gets views; the deadline is not changed.

## 1. "Monetized in 7-10 days": how they actually qualified

| Case (link) | Format and niche | Route they imply | Verdict |
|---|---|---|---|
| [E'Calm, "Shorts System That Got Me Monetized in 7 Days"](https://www.youtube.com/watch?v=-8BmzwwZhUk) (272K views, 2026-05-23; full transcript) | basketball Shorts, clips from TikTok re-edited | Shorts-views route implied, not stated | HYPE + COURSE. Channel created 2026-02-10 but "this account is 5 years old, use an old account, warm it up". Title says 7 days; he says "monetized in the same February" (up to ~18 days). 10M views in ~18 days would be ~550K/day; he says videos get 40K+. No subs or hours shown. Reused-content risk he admits. Gumroad courses, "$400K system" upsell, vidIQ affiliate link |
| [AI Cash Tom, "Skeleton Channel Got Monetized in 7 Days"](https://www.youtube.com/watch?v=umkq-HyBvH0) (962 views; full transcript) | AI skeleton Shorts, "What if you tried X for 1 year?" | Shorts route implied (claims 21M views/28 videos/1 month on a different channel) | UNVERIFIED. The 7-day claim is about someone else's channel, no analytics, no independent source found |
| [Arti Creator, "MONETIZED IN 7 DAYS"](https://www.youtube.com/watch?v=WZx_jYN9Gz4) (8K views, 2024) | faceless automation, "4-video strategy", "compilation cash cow" | not stated | metadata only; chapter titles point at compilations of existing videos |
| Medium "I Monetized a YouTube Channel in 7 Days" (shinefirstlk), Medium "...in 7 days with AI" (cosmoskay1), "Monetized in 5/8 Days to prove it's not luck" (Syrax), Gumroad/Payhip pages | mixed | none shown | pages returned 403 or empty; the Cosmos Kay snippet says "it took me nine days". Gumroad: sales pages, one sells pre-monetized channels. Not evidence |

What the numbers allow (ESTIMATE): 4,000 h = 240,000 viewed minutes inside 12 months, so a brand-new channel cannot get
there in 7-10 days without a viral hit. The only mechanically plausible fast routes are: (a) a viral Shorts run to 10M views
(about 555K views/day for 18 days), (b) an aged channel that already had subs/hours/views, (c) "monetized" meaning the
500-subscriber early-access tier (fan funding and shopping only, no ad share; search snippet of YouTube Help 13429240,
not opened), (d) a bought pre-monetized channel. The sources read do not say which one each person used. Official rules:
YouTube Help 72851 (opened) lists the two full routes and says Shorts-feed watch hours do not count. vidIQ's blog reports
that from 2027-02-01 the full tier doubles (8,000 h or 20M Shorts views); YouTube's own page as fetched only says updated
terms start 2027-02-01. Not confirmed; it is a reason not to slip past January 2027, not a change to our deadline.

Transferable from them, structure only: the first spoken line equals the title; the strongest motion first; one idea per
script that escalates. These match what the Bible Shorts winners do (section 3), not a monetization shortcut.

## 2. Sample and method

Pools (labels are kept in the JSON): **bible-short** 8 breakouts from 8 channels, **bible-long** 7 from 7 channels,
**cross-niche** 7 from 7 channels (six of the eight rows in the 11-02 cross pool were one cowboy cluster and are
excluded), **weak** 7 Bible longs + 8 Bible Shorts + 6 cross examples, **case-study** 3 read + 3 unreadable. Max channel
share 1/8, 1/7, 1/7 (limit 1/3). Window: published 2026-05 to 2026-11 (two rows carried from 11-02, flagged).
Structure maps from transcripts: 4 Bible Shorts, 5 Bible longs (+ 1 partial), 5 cross-niche (4 new + the 11-02 audit).
**Gap against the order:** 5 cross-niche maps, not 6 (10 credits were left under the cap); 2 Bible Shorts have no
captions (PB94aZkknfA 1.37M, 1L5oHMbZeho) and were not watched (a watch costs more). Timestamps are ~15 s blocks.
`vidiq_outliers` was not used (it returned an off-topic list on 11-04 whatever the query); `vidiq_youtube_search`
returned subs, views, outlier score and length per row.

Breakout evidence (views MEASURED 2026-11-04; subs MEASURED; outlier VIDIQ_MODEL):

| Video | Channel (subs) | Views | Len | Published | Title (abridged) | Thumb |
|---|---|---|---|---|---|---|
| [PB94aZkknfA](https://www.youtube.com/shorts/PB94aZkknfA) | Bible Chronicles (2.7K) | 1.37M | 1:08 | 09-23 | The Bitter Water of Marah (label) | not read |
| [RmhywUMP3i4](https://www.youtube.com/shorts/RmhywUMP3i4) | Apostles And Prophet Tv (17.5K) | 2.67M | 2:12 | 10-14 | THE DEMON LEFT THE BOY! | dark close faces |
| [CuQ1-DJVniI](https://www.youtube.com/shorts/CuQ1-DJVniI) | The Faith Archives (43K) | 1.41M | 2:54 | 08-26 | Ezekiel in the Valley of Dry Bones: Most Powerful Vision | not read |
| [ohJdEFM3MPQ](https://www.youtube.com/shorts/ohJdEFM3MPQ) | Bible & Reality TV (218K) | 2.72M | 1:18 | 07-26 | Why did God remove the Garden of Eden from Earth? | not read |
| [1L5oHMbZeho](https://www.youtube.com/shorts/1L5oHMbZeho) | Bible Hidden Truth (1.4K) | 57K | 0:11 | 09-20 | Who Really Stopped the Giants...? | not read |
| [I8tEhxU8hHQ](https://www.youtube.com/shorts/I8tEhxU8hHQ) | The Bible Story House (1.2K) | 20K | 0:29 | 10-28 | He Built a Giant Ship on Dry Land. Then It Rained | not read |
| [FaYEXkK6RsA](https://www.youtube.com/watch?v=FaYEXkK6RsA) | Bible Stories TV 247 (n/a) | 397K | 27:54 | 10-08 | NOAH AND THE GREAT FLOOD / The Full Bible Story | hero face + gold name |
| [et-vCpWWdQU](https://www.youtube.com/watch?v=et-vCpWWdQU) | Tales From Ancient Lands (8.6K) | 499K | 14:16 | 05-16 | Adam and Eve - The Full Story | pair + serpent + name |
| [eQB06k2CDlg](https://www.youtube.com/watch?v=eQB06k2CDlg) | EyeBible (42.6K) | 508K | 13:10 | 05-31 | The Most Dangerous Man In The Bible: The FULL Story Of Benaiah | hero + one word |
| [wFn6ZQWsVpY](https://www.youtube.com/watch?v=wFn6ZQWsVpY) | HolyBibleVerse tv (5.6K) | 569K | 15:11 | 08-19 | David and Goliath: The Great Battle / Full Movie | action frame + name |
| [JMz4iCPMo8w](https://www.youtube.com/watch?v=JMz4iCPMo8w) | Stories of the Olives (59.6K) | 665K | 19:30 | 05-23 | The Story of Lucifer Falling From Heaven | winged figure + name |
| [zURuppTrHro](https://www.youtube.com/watch?v=zURuppTrHro) | Bible Stories (3.9K) | 35.5K (11-02) | 20:36 | n/a | Why God Cast Adam & Eve Out of Eden | question text + pair |
| [_WD8NVhD5Ps](https://www.youtube.com/watch?v=_WD8NVhD5Ps) | Owens Bible (20.5K) | 710K | 8:41 | 10-15 | Unexpected Discoveries That Confirm The Bible | not read |
| [uhj_fjAgc6I](https://www.youtube.com/watch?v=uhj_fjAgc6I) | Era Reborn Tamil (16.7K) | 1.06M | 13:44 | 08-27 | How the Dutch Stole Thiruchendur Murugan | not read |
| [Lwq9JVCljq0](https://www.youtube.com/watch?v=Lwq9JVCljq0) | Extreme Survival Stories (32K) | 194K | 16:14 | 10-10 | 117 Days Lost at Sea | not read |
| [LyR4KxJ1-s0](https://www.youtube.com/watch?v=LyR4KxJ1-s0) | Appalachia Channel (64K) | 566K | 10:48 | 09-07 | America's MOST EVIL Man: Moses Harshaw | not read |
| [HU68FClr82M](https://www.youtube.com/shorts/HU68FClr82M) | Himanshu Uncovers (37K) | 14.7M | 2:42 | 08-24 | Real Life Dhurandhar: Neera Arya's Untold Story | not read |
| [vnCaetgtVmw](https://www.youtube.com/watch?v=vnCaetgtVmw) | Lost Snapshots (125) | 10.9K | 14:16 | 10-31 | 100 Extraordinary Historical Photos | not read |
| 93wYHx79Mso | Frontier Ever After (1.0K) | 8.6K | 27:51 | 10 (11-02) | premise-first cowboy romance | not read |

Also carried from 11-02: Cleed AIAkc2Gkamo (15K), Echoes of Scripture uhwNfZjs4n4 (12K), The Long Fear dHp3IpHMYrU (93K, 3 h).
Caution: the 2026-11-01 note took the "strongest hook" from bOvEdvjydhs, a video with 1,100 views (breakout 5.1); the
367K winner (FaYEXkK6RsA) opened calmly. Our long hook was modelled on the weak one.

## 3. Structure maps (timestamps ~+/-15 s; full maps in `structure-maps.json`)

**Bible Shorts (mapped n=4)**
- CuQ1 (2:54): 0:00 stakes + God's question "Can these bones live?" inside 5 s; question repeated 0:33 (loop 1); 1:09 payoff
  starts; 1:41 "but completely lifeless" (loop 2); 1:56 breath; 2:44 comment-question CTA.
- ohJd (1:18): line 1 is the title question verbatim; 0:05 "the answer is astonishing"; time jump 0:16; chained "Then Paul...
  Then Jesus..." 0:50; reframe 1:05; "drop an amen" 1:12.
- I8tE (0:29): line 1 is the title: act + mockery + reversal ("Then it rained"); whole story in 29 s; the transcript ends
  mid-sentence ("After every storm there is"): INFERRED loop into line 1.
- Rmhy (2:12): cold open mid-crisis, first speech 0:07; belief line 0:44; command 1:03; narrator explains only after the
  climax (1:39). May be re-cut film footage (not verifiable): not a model for originality.

**Bible longs (mapped n=5 + 1 partial)**
- Tales From Ancient Lands (14:16): calm open (no question); 7 turns + 5 "think about that" insights; end-only CTA; the
  Genesis 3:15 promise at 12:51 bridges to Jesus; chapter list in the description every ~1.2 min.
- EyeBible (13:10): cold open in the lion pit 0:00; freeze + "we must return to the beginning" 0:24 (closed 1:02);
  title promise at 0:47; forward hook 1:34 paid 6:12-11:06; dramatic irony 7:34; four set-pieces of 1.5-6 min.
- HolyBibleVerse (15:11): dialogue cold open; 0:14 one-line thesis; 0:32 flash-forward of the payoff line; 0:50 "we must
  return to the beginning" (same device as EyeBible: INFERRED shared script template); three closing paragraphs 13:41-15:01.
- Stories of the Olives (19:30): "Before he became Satan, he was heaven's brightest creation" (identity reversal);
  title promise only at 2:10; ~19 verse citations (one per ~60 s); 6 re-hooks, longest gap 4.8 min; ends bridged to Eden.
- Bible Stories 3.9K (20:36): slideshow, one plain sentence per ~25 s, no hook, no loop; the title question is answered at
  ~10-11 min. It wins on title + thumbnail + length + topic.
- FaYEXkK6RsA (27:54): calm 0-30 s, subscribe plea 1:02 (11-01 read).

**Cross-niche (mapped n=5)**
- Era Reborn Tamil (13:44): 0:00 question "what happens if a god's idol is thrown into the sea?"; 0:48 the idol gives a
  concrete clue (lemon + hawk); rewind 1:20; clue recalled 7:19 and found 9:00 (loop open 6.5 min); sung refrain every ~2 min
  (0:32, 3:25, 5:16, 8:11, 10:20); 13:14 "answer in the next video".
- Extreme Survival (16:14): date/place/inciting event 0:01; subscribe at 0:32 before the story restarts 0:49; a day counter
  (60, 80, 100, 117) carries the title number; two false rescues (8:35, 11:17); decision against despair 12:06; rescue 13:10.
- Appalachia (10:48): superlative claim 0:00; proof shown first (the tombstone) 0:15; promise 0:32; one atrocity per ~1.5 min;
  twist 10:13; three comment questions at the end; a folksy persona ("Well, anyways").
- Himanshu Uncovers Short (2:42): static image + "this really happened" + the shocking fact in 8 s; question at 0:12;
  promise 0:16; a beat per ~15 s; payoff 2:09; loop-back to the title idea 2:25.
- Frontier Ever After (11-02 audit): premise in two sentences 0-15 s = title; 4 loops paid 20:13-24:45; three narrator asides.

## 4. Synthesis: recurring patterns with counts

**Shorts, Bible (n=8 for stats, n=4 mapped)**
- Opening is stakes, a question or an event, never an introduction, greeting or reference to a prior part: 4/4.
- First line restates the title or its paradox: 2/4 (verbatim in both). Question inside 5 s: 2/4. Cold open in-scene: 1/4.
- Title: question/paradox 3/8, superlative or number 4/8, plain label 1/8. Comment-question CTA in the last 15 s: 2/4.
- Length: 11, 29, 68, 73, 78, 81, 132, 174 s (median 75.5; 6/8 are <=90 s). Combined with the 10-26 audit (5 of 6 at 170-179 s)
  both windows win (14 breakouts: 6 at >=170 s, 6 at <=90 s, 2 between): length is NOT a proven driver.
- 7/8 channels have under 50K subs; 4/8 have 1M+ views. The loop mechanic is rare and unproven (1 INFERRED).

**Longs, Bible (n=6 mapped)**
- "Full Story/FULL/Full Movie" in the title 4/6; a question 1/6; "The Story of" + name 1/6. Thumbnail = a face or pair + 1-3 baked-in
  words, 6/6 (viewed). Length 13:10-27:54, 6/6. Views per sub 9x-101x (ESTIMATE, MEASURED inputs).
- Cold open (scene or paradox) 3/6; calm or no hook 3/6 (these three are the Noah, Adam & Eve and Eden topics with the highest
  search demand). The narrative winners re-hook every 1.8-3.1 min on average (longest gap 4.8 min), 4/4.
- CTA only at the end 4/6; before 2 min 1/6 (and the cross-niche Survival video, 0:32).

**Cross-niche (n=5 mapped)**
- Premise or claim inside 15 s: 5/5; a question: 2/5; a concrete sign shown early and paid late: 3/5; a recurring motif
  (refrain or persona asides): 2/5; ends on a next-video tease: 2/5; comment-question CTA: 3/5.

**Winners vs weak (>=6 Bible contrasts; `weak-contrasts.json`)**
- Weak longs (n=7, about 24 days old, 11-3,628 views, subs 62-81K): 6/7 label/chapter/episode titles; 5/7 under 10 min, four of them
  4:15-6:39 (two are reading/audio formats); 0/7 name a conflict or promise in the title.
- Weak Shorts (n=8, 103-1,020 subs, 2-455 views): 5/8 label or verse titles; 3/8 curiosity titles that still got 77-156 views.
- So a curiosity title is not sufficient (3 weak Shorts have one; one weak long has 62 views at 62 subs with a good topic;
  a 50.8K-sub documentary got 352 views). Not separable here: thumbnail of the weak ones, seed audience, upload hour, topic demand.
  Five of the seven weak longs are Genesis 5 (a genealogy): title and topic are confounded.

## 5. Diagnosis of HeroVerse against it (ranked by effect on the binding constraint, long hours)

Our data (MEASURED, reports 11-03/11-04): subs 316; own public long hours 28.8 (ESTIMATE; Studio counter unread); Shorts
169-687 views; longs 3-15 views (flood-ends-long 5, Noah Genesis 5-7 3; the prayer longs 94-103 with 430-541 s average view);
public Shorts views last 90 d 2,668.

1. **Long package and length (largest).** Titles: "The Flood Ends: The Raven, the Dove and the Rainbow (Genesis 8-9, KJV)" and
   "Noah's Ark and the Flood Begins: Genesis 5-7" are label titles (the weak pattern, 6/7); Babel's question title is in the winning
   pattern. Length: flood-ends-long is 8:22 and the built Babel long is 483.8 s (8.1 min, below the 13-min floor of 6/6 winners),
   while the live plan targets 900 s. Thumbnail rule: none recorded; winners 6/6 face + name. Expected effect: highest, because
   hours = views x minutes and both are low; this is the lever the 11-01/11-02 findings pointed at.
2. **Unused demand we can serve without generation.** The proven search lane in our order is Noah ("Full Bible Story of Noah",
   397K views in 27 days, MEASURED) and Adam and Eve (2 winners, 35.5K and 499K). The Noah compilation title already follows the
   winning mechanic; the second compilation "Creation to Cain (Genesis 1-4) KJV" does not name the Adam and Eve demand or
   carry a question/"Full Story" element. Zero-cost, uses approved media.
3. **Long opening content.** Our hook is two stacked rhetorical "What if" questions (modelled on a 1,100-view video). 3/6 winners
   open in a scene, 3/6 do not need a hook; none of the six opens on stacked abstract questions. Medium effect on retention (not
   measurable for others); keep the God-line flash-forward and add the in-scene cold open + the "return" device + title promise by
   ~50 s.
4. **Shorts' first line and length (subs, second constraint).** Our openings lean on the previous part ("Those words were
   spoken over the whole world", "One man heard those words"), our bridges run 167-179 s, and the title suffix is a series label.
   Winners open on stakes/question/event (4/4) and 6/8 are <=90 s. Effect: subs/day (2.9 now vs 25.6 needed for 12-01).
5. **Shorts to long hand-off.** 0 long views from Shorts (MEASURED, 11-04 report). No winner in the sample shows a hand-off; their
   Shorts are stand-alone. Treat the funnel as a long-term support, not as the hours engine.
6. **Re-hook cadence.** Our long structure already requires a re-hook at every chapter end and a climax at 0.6-0.85, in line
   with 4/4 narrative winners (1.8-3.1 min mean gap): no gap, keep.

## 6. Which YPP route fits the deadline (target 2026-11-15, max 2026-12-01; unchanged)

Shorts route (10M public Shorts views in 90 days + 1,000 subs): needs 111K views/day over 90 days or about 370K/day to land by
12-01 (ESTIMATE, 10,000,000 / 27). We have 2,668 in 90 days and our best video in the 11-03 report has 4,397 views, so 10M equals about 2,300 of
our best video in the 11-03 report. The best Bible Shorts channel in the sample (218K subs) put 9.0M views on five videos over about five weeks
(MEASURED sum). Not reachable; do not re-plan around it. The Shorts still serve the second requirement, 1,000 subs (684 to go).

Long-hours route (1,000 subs + 4,000 h): 3,971 h to go. Arithmetic (ESTIMATE): 40,000 views at 6 min, or 16,000 views at 15 min,
or 8,000 views at 30 min (a 60-min compilation at 50% retention) all give 4,000 h. One FaYEXkK6RsA-class video (397K views in
27 days) would exceed it at an average view of only 36 s. A zURuppTrHro-class video (35.5K views, 20.6 min) needs an average view
of 6.7 min. So the route works only if one long breaks out; session length (compilations) cuts the views needed by 3-7x. This is
the plan's existing direction: put capacity on long packages and long compilations, keep the Shorts as the subs engine.
Not changed: the deadline; no gate; no spending.

## 7. Production specs (apply from the next build; none edits a frozen QA file or gate)

**Hook template, long (first 60 s)** (3 slots, in order):
1. 0-25 s: the title's conflict seen in a scene at its most dangerous moment (our God-line flash-forward or an acted line), one
   concrete detail, no stacked abstract questions; or one identity-reversal sentence (Olives pattern).
2. By ~50 s: the title promise stated in one sentence ("this is the story of ...", EyeBible 0:47).
3. A return device when a cold open is used ("to understand, we must go back"), closed within ~60 s; and one forward hook
   (what they did not know yet) by ~1:30 that is paid in the second half. Calm openings are allowed only for high-demand
   "Full Story" packages (3/6 winners).

**Title rules, long**: (a) a "Full Story"/"Complete Story" element OR a question OR "the most [superlative] ... in the Bible" with the
protagonist's name in the first 40 characters; (b) the Genesis reference and "(KJV)" after the pipe; (c) never a chapter label,
"Part N", an episode number or "audio reading" as the title (6/7 weak); (d) one story per video. Examples of the mechanic, not
copy: "Why Did God <do X>? | The Full Story of <Name> | Genesis N (KJV)"; "The <superlative> <role> in the Bible: The FULL Story
of <Name>"; compilations "The Complete Story of <Name> (Genesis A-B) KJV". Adam and Eve is the strongest observed demand: title the
Creation-to-Cain compilation around Adam and Eve and the question of why God sent them out, with the Genesis 1-4 range.

**Thumbnail rules (long, viewed 6/6)**: one face or a pair at about 40% of the frame in a strong emotion or action; at most 4 baked-in
words (the protagonist's name, or the title question); one story object (ark, spear, serpent, tower); high contrast gold/white
on dark or a saturated scene; the thumbnail text complements the title, it does not repeat it; no Keeper in the thumbnail (not
tested). Test one attribute at a time with Studio Test & Compare (existing rule).

**Length**: new story longs 13-20 min (floor 13:00, from 6/6 winners); compilations 40-60 min. The Babel build (8.1 min) is below
the floor: it is a decision for the coordinator under the frozen gates, not changed here.

**Re-hook cadence, long**: a turn or open loop at least every 3 min, never a gap above 5 min; 2-3 "think about that" insight lines
per 10 min (marked as commentary, not scripture); one verse citation roughly every 1-2 min where the text allows; comment-question CTA
only in the last 30 s; no subscribe plea before the payoff; the last 20 s name the next story (end screen target).

**Short template (stand-alone, 60-90 s variant A; the 170-s bridge stays variant B)**:
- 0-3 s: one spoken line, <=14 words, that states the stake or the paradox of the title; never refers to a previous part.
- 3-10 s: who and what is at risk. 10-55 s: two or three escalations, each ending on an unresolved line. 55-68 s: the payoff with one
  exact KJV line. 68-75 s: one answerable comment question; the last clause is written so it can lead back into line 1.
- Title: the hook line first (question, paradox, number or superlative), reference and "(KJV)" after; no label-only titles.
- Test: one of the 4 daily Shorts as variant A for 7 days (7 Shorts); success = median views >= 2x the median of the variant-B
  Shorts in the same days; kill = <= 1x. Sparse data stays INCONCLUSIVE; length stays "unproven driver".

**Cadence**: unchanged (4 Shorts/day by owner rule; one new long per story, one compilation per arc). The evidence gives no
cadence effect; the change is in what each slot contains. Re-package the oldest published longs (title and thumbnail only,
never the accepted media) with the title rules above, one attribute per test.

## 8. Limits and next tests

- CTR, retention, impressions and subscriber conversion of the winners are NOT_MEASURED; transcripts are a proxy. A structure
  that shows up in winners and weak alike (11 attributes in the 10-26 audit) cannot be the cause.
- The weak sample is 24 days old, topic-confounded (Genesis 5) and its thumbnails were not read.
- Cross-niche: 5 of 6 maps; two Shorts without captions; Tamil/Hindi translated by Claude.
- Content cautions: two Bible Shorts winners use non-canonical material (2 Enoch, giants at the ark) and one may be re-cut film;
  our KJV-only and original-media rules apply. Pattern only.
- Next tests (zero cost): (1) repackage one published long (title + thumbnail) under the rules; read 7-day views and CTR in Studio;
  (2) variant-A Short vs variant-B; (3) the Creation-to-Cain compilation titled and thumbnailed on the Adam and Eve demand; kill
  rule from the live plan (<100 views in 7 d).
