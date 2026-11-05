# Keeper lip-sync with our audio: model and free-compute research (2026-11-05)

Owner, 2026-11-05: "No guardião eu quero lixo sync pra ele falar.. verifique algo gratuito e de qualidade" (lip-sync). Goal:
our exact Kokoro line on a Pavo silent frontal Keeper clip, so the Keeper speaks and Pavo never garbles a word. Labels:
VERIFIED = read from the repository, model card or measured in a run; CLAIMED = a source says it, not checked here.

## Models (license of code AND weights, commercial use, hardware)

| Model | Code | Weights | Needs | Verdict |
|---|---|---|---|---|
| MuseTalk 1.5 (TMElyralab, 2025-03) | MIT (VERIFIED, repo LICENSE and README "no limitation for both academic and commercial usage") | MIT on the HF card (VERIFIED); README: "for any purpose, even commercially" | one UNet step per frame on a 256x256 face crop; 4 GB VRAM fp16 (README) or CPU (VERIFIED, ran on a 4-vCPU Actions runner) | CHOSEN: only candidate that finishes on free CPU |
| LatentSync 1.5 / 1.6 (ByteDance) | Apache-2.0 (VERIFIED) | OpenRAIL++ (VERIFIED, HF card; use-based restrictions, commercial use allowed) | 8 GB (1.5) / 18 GB (1.6) VRAM (README, VERIFIED); 20-step diffusion per 16 frames; `.to("cuda")` hard-coded; face detector is insightface `FaceAnalysis` (CUDAExecutionProvider) whose pretrained models are research-only (CLAIMED, insightface terms) | GPU route only, after replacing the detector; cost on CPU estimated in hours (not run) |
| Wav2Lip | non-commercial (CLAIMED, repo/licence text: research and personal use) | same | small | REJECTED: the channel is monetized |
| SadTalker, video-retalking, EchoMimic, InfiniteTalk | not read (older, non-lip-region-only or ~28 GB weights) | | | not pursued: heavier than MuseTalk or full-head re-render that would change the approved Keeper identity |
| Sync Labs, Hedra, Runway lip-sync | hosted | paid | | paid, rejected (no new spending) |

Third-party files MuseTalk loads (each pinned by sha256 in `keeper_lipsync.PINS`): sd-vae-ft-mse (MIT, HF card), whisper-tiny
(Apache-2.0, HF card), DWPose `dw-ll_ucoco_384.pth` (Apache-2.0, HF card), S3FD `s3fd-619a316812.pth` (face-alignment BSD-3;
S3FD itself was trained on WIDER FACE, CLAIMED research data), BiSeNet face-parse `79999_iter.pth` (zllrunning MIT code;
trained on CelebAMask-HQ, whose dataset terms are non-commercial research, CLAIMED). The last two are the only gray items;
both only find a face box and a blending mask, they do not generate the Keeper's likeness. The owner may want to know.

## Where it runs (free), in the order asked

1. GitHub Actions CPU (zero setup): WORKS. `lipsync.yml`, ubuntu-24.04 (4 vCPU, 16 GB), Python 3.10 venv, torch 2.0.1 cpu,
   mmcv 2.0.1 cpu wheels. Environment 80-90 s. Measured on the 720p 24 fps Keeper clip (7.05 s, 170 frames): face boxes
   every 8th frame 53-64 s, UNet+VAE ~4.4 s/frame, blending ~0.2 s/frame, 746-911 s inference, 940-1070 s whole job.
   Out of the box the model's own landmark pass costs 3.2 s/frame and made the 3 s probe take 757 s (and a 7 s line over
   37 min before it was cancelled); sparse boxes (static camera) remove it. Runner speed varies 2x: the 7.05 s line took 746-911 s of inference, the 5.05 s line 1407 s on a slower runner (whole
   jobs 15.7, 17.8 and 26 min). So 2-4.7 minutes per second of picture: an 8 s clip 16-37 min, 10 s 20-47 min. Always inside a 6 h job
   but the 20-minute-per-10-s target is met only on a fast runner; keep Keeper clips short (8 s or less). Public-repo runner minutes are free (the repo is public: CLAIMED from the earlier ops notes).
2. The owner's PC (device "Matheus", offline; NVIDIA MX330 with 2 GB VRAM and 8 GB RAM per the owner): RULED OUT. MuseTalk's
   smallest tested setup is 4 GB VRAM fp16 (README), LatentSync 1.5 needs 8 GB. Do not plan any local run.
3. Free hosted GPUs (documented, no account created): Kaggle notebooks (CLAIMED about 30 GPU h/week, T4/P100, 9-12 h sessions,
   manual notebook, no CI); Colab free (CLAIMED unpublished 15-30 h); Hugging Face ZeroGPU (docs: 5 min of GPU a day on a free
   account, charged by requested duration, CLAIMED 3 runs/day; needs a Space, a verified email and a 30-day-old account).
   To use one the owner creates the account and stores its token as a GitHub secret (KAGGLE_KEY / HF_TOKEN); not needed now.

## Quality, measured (same gates as Pavo-native clips; thresholds unchanged)

SyncNet through `lipsync_check` (offset must be -3..0, confidence >= 2.7; Pavo-native clips passed at 6.8-8.6):

| Clip + line | Lip-synced offset / conf | Same silent clip with the line laid over it (control) | Flags |
|---|---|---|---|
| keeper-vo probe-k-close-1 + genesis07 k-close.wav (6.55 s) | 0 / 3.13 (171 windows), face 100 % | -13 / 0.59 (MOUTH_NOT_IN_SYNC) | none |
| keeper-vo probe-k-question-1 + genesis07 k-question.wav (4.55 s) | 0 / 3.30 (121 windows), face 100 % | -15 / 0.95 (MOUTH_NOT_IN_SYNC) | none |

A third pair (probe-k-insight-1 + k-insight.wav) was refused by the source gate itself (`LIPSYNC_SOURCE_FACE_NOT_FOUND`, face in 79 % of the
silent clip, run 42026771307): the gate works and was not loosened. Evidence: `evidence/lipsync/20261105/` (runs 42024334433, 42027139703).

Reading: the lips follow our audio (the control is 13 frames off and unreadable, the result offset 0), our audio is bit-exact
(`pavo_audio.assert_ours`), the face is found in every frame, no clip artifact. But the confidence is 3.1 against 6.8-8.6
for Pavo-native lips: it passes the gate by a margin of 0.4, it is a mouth that is right but not Pavo-sharp. Frame sheet
(`sheet-compare.jpg`): the lower face is a visibly softer 256 px patch (MuseTalk's face region is 256x256; the README itself
suggests GFPGAN), the beard hides most of the lip shape, no seam or flicker was seen in the sheet. Claude looked at stills only;
nobody has watched and heard the clip, so it is NOT an approval and no 9.5 is claimed. LatentSync's papers report higher
LSE-C than MuseTalk (CLAIMED): the GPU route is the upgrade if the owner finds the softness unacceptable.
