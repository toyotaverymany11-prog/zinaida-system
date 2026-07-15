# HyperFrames Video Generation Workflow

This reference provides detailed instructions for creating videos with HyperFrames using HTML, CSS, and JavaScript compositions.

## Overview

HyperFrames treats HTML as the video source of truth. Build video scenes as HTML compositions with CSS layout and JavaScript animation, validate the layout, then render the result to MP4.

HyperFrames is ideal for:
- Short video intros and cinematic trailers
- Product promos and marketing videos
- Subtitle animations and captions
- HUD/tech visuals and motion graphics
- Web-to-video conversions (converting web content to video)

## Prerequisites

- Node.js installed
- FFmpeg installed (for rendering)
- HyperFrames CLI installed (`npx hyperframes`)
- Hermes Web UI (optional, for some features)

## Installation

If HyperFrames is not installed:

```bash
hermes skills install official/creative/hyperframes
```

## Project Setup

### Initialize a New Project

```bash
npx hyperframes init my-video --non-interactive
```

This creates a new HyperFrames project with the basic structure.

### Project Structure

```
my-video/
├── src/
│   ├── index.html          # Main composition
│   ├── styles.css          # CSS styles
│   ├── script.js           # JavaScript animation
│   └── assets/             # Images, fonts, etc.
├── package.json            # Project configuration
└── .hyperframesrc          # HyperFrames configuration
```

## Composition Development

### HTML Composition Structure

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>My Video Composition</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <div class="composition"
       data-composition-id="main"
       data-width="1920"
       data-height="1080"
       data-duration="30">
    
    <!-- Scene 1 -->
    <div class="scene" data-start="0" data-duration="10" data-track-index="0">
      <h1 class="title">Welcome</h1>
    </div>
    
    <!-- Scene 2 -->
    <div class="scene" data-start="10" data-duration="10" data-track-index="1">
      <p class="subtitle">To My Video</p>
    </div>
    
    <!-- Scene 3 -->
    <div class="scene" data-start="20" data-duration="10" data-track-index="2">
      <img src="assets/logo.png" class="logo">
    </div>
  </div>
  
  <script src="script.js"></script>
</body>
</html>
```

### CSS Styling

```css
/* Base styles */
body {
  margin: 0;
  padding: 0;
  background: #000;
  overflow: hidden;
}

.composition {
  position: relative;
  width: 1920px;
  height: 1080px;
  font-family: Arial, sans-serif;
}

.title {
  font-size: 120px;
  color: #fff;
  text-align: center;
  margin-top: 400px;
  font-weight: bold;
}

.subtitle {
  font-size: 60px;
  color: #00ff00;
  text-align: center;
  margin-top: 300px;
}

.logo {
  position: absolute;
  bottom: 100px;
  left: 50%;
  transform: translateX(-50%);
  width: 300px;
}
```

### JavaScript Animation

```javascript
// Register GSAP timelines
window.__timelines = window.__timelines || {};

// Main timeline
tl = gsap.timeline({
  defaults: {duration: 1}
});

// Scene 1 animation
tl.to(".title", {
  opacity: 1,
  y: -50,
  ease: "power2.out"
});

// Scene 2 animation
tl.to(".subtitle", {
  opacity: 1,
  y: -30,
  ease: "power2.out"
}, "+=2");

// Scene 3 animation
tl.to(".logo", {
  opacity: 1,
  scale: 1,
  ease: "elastic.out(1, 0.5)"
}, "+=1");

// Store timeline
window.__timelines["main"] = tl;
```

## Development Workflow

### 1. Create Composition

Write your HTML/CSS/JS composition following the structure above. Focus on:
- Correct static layout first
- Then add animation
- Use GSAP for smooth animations

### 2. Validate Layout

```bash
npx hyperframes lint
```

This checks your composition for common issues:
- Missing composition ID
- Invalid dimensions
- Missing required attributes
- CSS errors

### 3. Inspect Composition

```bash
npx hyperframes inspect --samples 15
```

This renders sample frames to verify:
- Layout correctness at different timestamps
- Text readability
- Animation timing
- Visual consistency

### 4. Preview

```bash
npx hyperframes preview
```

Launches a preview server to see the video in real-time as you make changes.

## Rendering

### Render Options

```bash
# Draft quality (fast, for iteration)
npx hyperframes render --output draft.mp4 --quality draft

# Standard quality (balanced)
npx hyperframes render --output standard.mp4 --quality standard

# High quality (slow, for final delivery)
npx hyperframes render --output final.mp4 --quality high
```

### Custom Output Path

```bash
npx hyperframes render --output /path/to/output.mp4 --quality high
```

### Additional Options

```bash
# Specify composition ID
npx hyperframes render "main" --output output.mp4

# Set duration
npx hyperframes render --duration 30 --output output.mp4

# Set dimensions
npx hyperframes render --width 1920 --height 1080 --output output.mp4
```

## Composition Rules & Best Practices

### Required Elements

1. **Composition Container**:
   - Must have `data-composition-id`
   - Must have `data-width`
   - Must have `data-height`
   - Must have `data-duration`

2. **Timed Elements**:
   - Must have `data-start`
   - Must have `data-duration`
   - Must have `data-track-index`

### Animation Guidelines

1. **Deterministic Animation**:
   - Avoid `Math.random()` or `Date.now()`
   - Use seeded random if needed
   - Avoid infinite repeats

2. **Media Playback**:
   - Use HyperFrames runtime for media playback
   - Don't manually call `play()`, `pause()`, or seek

3. **Text Readability**:
   - High contrast text
   - Safe margins (don't put text at edges)
   - Adequate font size for target platform

4. **Performance**:
   - Test with `inspect` command
   - Optimize complex animations
   - Use CSS transforms for GPU acceleration

### Layout Validation

Always run these before rendering:

```bash
npx hyperframes lint
npx hyperframes inspect --samples 15
```

Check that:
- Text stays readable at all timestamps
- UI elements stay within frame
- Colors and contrast are correct
- Animation timing is as expected

## Delivery

When delivering a HyperFrames project, include:

1. **Rendered MP4 path** - The final deliverable
2. **Project files path** - Source HTML/CSS/JS
3. **Preview command** - How to view the project
4. **Assumptions made** - Duration, aspect ratio, style, etc.
5. **Validation results** - Any issues found and addressed

## Troubleshooting

### Common Issues

#### 1. Missing Node.js or FFmpeg

**Error**: `command not found: npx` or `FFmpeg not found`

**Solution**:
```bash
# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
apt-get install -y nodejs

# Install FFmpeg
apt-get install -y ffmpeg
```

#### 2. Render Failures

**Error**: Render command fails without clear message

**Solution**:
```bash
npx hyperframes doctor
```

This diagnoses common issues:
- Missing dependencies
- Configuration problems
- Environment issues

#### 3. Layout Issues

**Symptom**: Text or elements appear in wrong positions

**Solution**:
- Run `npx hyperframes inspect --samples 15`
- Check each sample frame
- Adjust CSS positioning
- Verify `data-start` and `data-duration` values

#### 4. Animation Not Working

**Symptom**: Animations don't play or play incorrectly

**Solution**:
- Verify GSAP is loaded
- Check `window.__timelines` registration
- Use `preview` command to test in real-time
- Verify timing calculations

## Performance Optimization

### For Large Projects

1. **Use CSS Transforms**:
   ```css
   transform: translateX(100px);
   ```
   Instead of:
   ```css
   left: 100px;
   ```

2. **Batch DOM Updates**:
   - Use GSAP's ` stagger` for multiple elements
   - Chain animations efficiently

3. **Optimize Images**:
   - Use appropriate image formats (WebP for web)
   - Compress images before adding to project
   - Use sprites for repeated elements

4. **Limit Complexity**:
   - Break complex scenes into multiple compositions
   - Reuse components and animations
   - Keep individual scene durations reasonable

## Use Cases by Category

### Marketing Videos
- Product demos
- Feature highlights
- Pricing announcements
- Customer testimonials

### Social Media Content
- Vertical short videos (1080x1920)
- Horizontal videos (1920x1080)
- Square videos (1080x1080)
- Animated captions and overlays

### Technical Videos
- API documentation with visuals
- Code walkthroughs
- Tutorials with screen recordings
- Data visualization animations

### Creative Projects
- Cinematic trailers
- Motion graphics
- Abstract animations
- Generative art videos

## Alternatives

If HyperFrames is unsuitable:
- Use **Remotion** for React-based video projects
- Use **Grok Image-to-Video** for quick prompt-driven animation
- Use **manual editing** for frame-by-frame precision
- Use **video editing software** for complex post-production

## References

- HyperFrames Official Documentation
- GSAP Animation Library
- Video Style Guide: `references/video-style-guide.md`
- Troubleshooting Guide: `references/troubleshooting.md`
- Composition Template: `templates/hyperframes-composition.html`