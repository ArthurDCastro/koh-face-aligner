# KOH Tutorial - How the app works

**Language:** 🇺🇸 **English** · 🇧🇷 [Português](koh-tutorial-pt-BR.md) · 🇪🇸 [Español](koh-tutorial-es.md)

This tutorial explains, in simple terms, how KOH works, which parameters it uses, and what each part of the interface does.

> Note: the app is designed to standardize portraits by detecting the main face, centering it, and exporting a final image in specific dimensions.

## 1. Overview of the workflow

The main process is:

1. receive one or more images;
2. locate the largest face in them;
3. adjust the face scale and position inside the final image;
4. apply the selected background mode;
5. save the results in an output folder.

In simple terms, the program tries to transform each detected face into a standardized composition, keeping the subject in the correct place and with consistent proportions.

## 2. What the app does behind the scenes

The main logic is split into a few steps:

- face detection with YuNet;
- selection of the largest detected face;
- alignment and resizing based on face proportion;
- crop and positioning in the final image;
- optional background removal.

The processing pipeline uses OpenCV, and in batch mode the app can process multiple photos sequentially.

## 3. How the interface is organized

The main application window contains the following areas:

### 3.1 Input image area

Here you select the photos to process.

- "Add Images" button for single files;
- "Add Folder" button for selecting an entire folder;
- "Clear" button to remove the current selection;
- file list to confirm the batch.

Space for illustrative image:

```md
![Illustrative image: selecting images in KOH](./images/placeholder-input-images.png)
```

> Add a screenshot here showing the file list and the selection buttons.

### 3.2 Output settings

This section defines the final composition:

- Width: output image width in pixels;
- Height: output image height in pixels;
- Face Ratio: how much of the final width the face occupies;
- Position X: horizontal shift of the face;
- Position Y: vertical shift of the face;
- Background Removal: the type of background treatment.

These parameters directly affect the final look.

Space for illustrative image:

```md
![Illustrative image: KOH output settings](./images/placeholder-output-settings.png)
```

> Add a screenshot or mockup of the configuration fields here.

### 3.3 Output folder

You choose the folder where the processed images will be saved.

The app creates the directory automatically if needed and saves the final images there.

Space for illustrative image:

```md
![Illustrative image: selecting the output folder](./images/placeholder-output-folder.png)
```

> Add an image of the destination folder selector here.

### 3.4 Progress bar and status

When processing starts, the interface shows:

- progress per image;
- overall processing status;
- success or error messages;
- the current batch state.

Space for illustrative image:

```md
![Illustrative image: processing progress bar](./images/placeholder-progress.png)
```

> Add a photo of the progress bar while work is running here.

## 4. What each setting does

### 4.1 Width

Defines the final width of the exported image.

If the width is too small, the face can look compressed. If it is too large, the face may appear too small in relation to the frame.

### 4.2 Height

Defines the final height of the image.

This affects the vertical spacing between the face and the image boundaries, which is important for portrait framing.

### 4.3 Face Ratio

This control determines how much of the final image width is occupied by the face.

Examples:

- lower value: the face takes less space;
- higher value: the face becomes larger in the composition.

In the code, the face is scaled to match the target proportion.

### 4.4 Position X

Defines the horizontal position of the face inside the final image.

- 50%: center horizontally;
- lower values: face more to the left;
- higher values: face more to the right.

### 4.5 Position Y

Defines the vertical position of the face.

- 40% is the default, which usually keeps the face slightly above the exact center;
- lower values: face higher;
- higher values: face lower.

### 4.6 Background Removal

Background removal can be configured in three modes:

#### Disabled

No background removal is applied. The final result keeps the original background, but the face is still centered and resized.

#### Fast

Uses a quick segmentation algorithm to isolate the subject and remove the background with a lighter processing approach.

#### AI

Uses MODNet, an AI model specialized in portrait matting. This mode generally produces a cleaner subject/background separation, especially in challenging lighting conditions.

## 5. How face detection and centering work

The app uses the YuNet detector to find faces.

### Step by step

1. the image is loaded;
2. the detector looks for faces;
3. the largest face is selected;
4. the face center is calculated;
5. the image is scaled based on the configured proportion;
6. the face is shifted to the target X/Y position;
7. the result is exported.

Mathematically, the program applies an affine transformation to move and scale the face into the final frame. This keeps the composition standardized even when people appear at different sizes or positions in the original image.

## 6. What happens for each processed image

For each file in the batch, the app:

- validates the image;
- loads the file;
- detects the main face;
- adjusts the composition;
- applies background removal if configured;
- saves the final image in the output folder.

If no face is detected, the processing is recorded as an error and the file is not saved.

## 7. Result export

Final files are saved with names like:

- `koh_<image-name>.jpg` when no background removal is used;
- `koh_<image-name>.png` when background removal is enabled.

These names help identify quickly that the image was processed by KOH.

## 8. How batch processing works

The app can receive:

- several images at once;
- an entire folder of images;
- a mix of files and directories.

Then it processes each item in sequence. The progress bar updates to show how much of the batch has already been completed.

Space for illustrative image:

```md
![Illustrative image: KOH batch processing](./images/placeholder-batch-processing.png)
```

> Add an image showing the app processing multiple images in sequence.

## 9. Tips for better results

- use photos where the face is clearly visible;
- prefer good lighting;
- avoid partially hidden faces;
- test Face Ratio and Position Y until the framing looks natural;
- if the background is complex, the AI mode usually gives cleaner results.

## 10. Quick summary

KOH is an app for standardizing portraits and exporting visually consistent results.

It works basically like this:

- detects the face;
- centers and resizes the face in the final image;
- adjusts the position and proportion;
- removes the background when needed;
- saves the final image.

If you understand these controls, you are ready to use the app and get good results quickly.

## 11. Next steps

- test with a single simple portrait to observe the effect of Face Ratio;
- adjust Position X and Position Y to change framing;
- compare Disabled, Fast, and AI modes to see the difference in background extraction;
- try a full batch to evaluate consistency across many images.

---

If you want, this tutorial can be expanded with:

- a step-by-step usage guide;
- a checklist of settings by portrait type;
- before/after examples for each background mode.
