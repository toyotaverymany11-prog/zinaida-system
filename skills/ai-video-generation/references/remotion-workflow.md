# Remotion Video Generation Workflow

This reference provides detailed instructions for creating videos with Remotion, a React-based video framework.

## Overview

Remotion is different from prompt-only AI video tools: it produces a code project. That means you can repeatedly edit subtitles, timing, characters, scenes, voiceover, sound effects, and visual rhythm, then render a new MP4.

Remotion is ideal for:
- Vertical short videos (1080x1920)
- Product demos and tutorials
- Story-driven animations
- HUD/tech-style visuals
- Feed ad creatives
- Reusable video templates
- Code-based video iteration

## Prerequisites

- Node.js installed (v16+ recommended)
- npm or yarn
- FFmpeg installed (for rendering)
- Chrome browser (for Remotion Studio)

## Installation

### Install Remotion CLI

```bash
# Install globally
npm install -g remotion

# Or use npx for project-specific installation
npx create-video@latest --yes --blank --no-tailwind my-video
```

### Project Setup

```bash
# Create new project
npx create-video@latest --yes --blank --no-tailwind my-video

cd my-video
```

## Project Structure

```
my-video/
├── src/
│   ├── api.ts              # API calls and data fetching
│   ├── components/
│   │   ├── Scene1.tsx       # Individual scene components
│   │   ├── Scene2.tsx
│   │   └── ...
│   ├── composition.tsx     # Main composition definition
│   ├── constants.ts        # Configuration and constants
│   ├── styles.css          # Global styles
│   └── index.tsx           # Entry point
├── package.json            # Project configuration
├── tsconfig.json           # TypeScript configuration
└── remotion.config.js      # Remotion configuration
```

## Development Workflow

### 1. Create Production Brief

Turn the user's request into a concise brief:
- Purpose and audience
- Duration and aspect ratio
- Style and visual language
- Scenes and content structure
- Text, narration, music, and sound effects
- Output path and format

**Default Recommendations:**
- Vertical short video: 1080x1920, 30fps
- Horizontal video: 1920x1080, 30fps
- Duration: Platform-appropriate (e.g., 30s for TikTok, 60s for YouTube Shorts)

### 2. Build Video Components

Create React components for each scene:

```tsx
// src/components/Scene1.tsx
import { AbsoluteFill, useCurrentFrame } from 'remotion';

const Scene1 = () => {
  const frame = useCurrentFrame();
  const progress = Math.min(frame / 30, 1); // 1 second animation
  
  return (
    <AbsoluteFill style={{ backgroundColor: '#000' }}>
      <div style={
        {
          fontSize: 120,
          color: '#fff',
          textAlign: 'center',
          marginTop: '40%',
          fontWeight: 'bold',
          transform: `translateY(${50 * (1 - progress)}px)`
        }
      }>
        Welcome
      </div>
    </AbsoluteFill>
  );
};

export default Scene1;
```

### 3. Define Composition

```tsx
// src/composition.tsx
import { Composition } from 'remotion';
import Scene1 from './components/Scene1';
import Scene2 from './components/Scene2';

const MyVideo = () => {
  return (
    <>
      <Composition
        id="Scene1"
        component={Scene1}
        durationInFrames={30} // 1 second at 30fps
        fps={30}
        width={1080}
        height={1920}
      />
      
      <Composition
        id="Scene2"
        component={Scene2}
        durationInFrames={60} // 2 seconds
        fps={30}
        width={1080}
        height={1920}
      />
    </>
  );
};

export default MyVideo;
```

### 4. Preview in Studio

```bash
npx remotion studio
```

This launches Remotion Studio where you can:
- View all compositions
- Scrub through timeline
- Test animations in real-time
- Make iterative edits

### 5. Validate

Before rendering, validate your project:

```bash
# Build project
npm run build

# Render a still frame for inspection
npx remotion still Scene1 --scale=0.25 --frame=15

# Check for errors
npm run lint
```

## Rendering

### Render Command

```bash
# Basic render
npx remotion render Scene1 out/Scene1.mp4

# With custom output path
npx remotion render Scene1 /path/to/output.mp4

# High quality render
npx remotion render Scene1 out/Scene1.mp4 --quality 2
```

### Render Options

```bash
# Set output directory
npx remotion render Scene1 out/ --every-frame

# Custom framerate
npx remotion render Scene1 out/video.mp4 --fps 60

# Custom dimensions
npx remotion render Scene1 out/video.mp4 --width 1920 --height 1080

# Concurrency (for faster rendering)
npx remotion render Scene1 out/video.mp4 --concurrency 4
```

### Batch Rendering

```bash
# Render all compositions
npx remotion render all out/

# Render specific compositions
npx remotion render "Scene1 Scene2" out/
```

## Advanced Techniques

### Using Assets

```tsx
import { Img, Video, Audio } from 'remotion';

// Static image
<Img src={require('./assets/logo.png')} />

// Video
<Video src={require('./assets/demo.mp4')} />

// Audio
<Audio src={require('./assets/music.mp3')} />
```

### Timing and Animation

```tsx
import { useCurrentFrame, interpolate, spring } from 'remotion';

const MyComponent = () => {
  const frame = useCurrentFrame();
  const videoConfig = useVideoConfig();
  
  // Simple fade-in
  const opacity = interpolate(
    frame,
    [0, 30], // from frame 0 to 30
    [0, 1],  // from 0 to 1 opacity
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );
  
  // Spring animation
  const scale = spring({
    frame,
    fps: videoConfig.fps,
    from: 0.8,
    to: 1,
    config: {
      damping: 100,
      stiffness: 200,
    },
  });
  
  return <div style={{ opacity, transform: `scale(${scale})` }}>Content</div>;
};
```

### Sequences and Parallel Timelines

```tsx
import { Sequence } from 'remotion';

const MyComposition = () => {
  return (
    <>
      {/* First scene: 0-30 frames */}
      <Sequence durationInFrames={30} from={0}>
        <Scene1 />
      </Sequence>
      
      {/* Second scene: 30-90 frames (60 frames duration) */}
      <Sequence durationInFrames={60} from={30}>
        <Scene2 />
      </Sequence>
      
      {/* Third scene: 90-120 frames (30 frames duration) */}
      <Sequence durationInFrames={30} from={90}>
        <Scene3 />
      </Sequence>
    </>
  );
};
```

### Using Audio

```tsx
import { Audio } from 'remotion';

const SceneWithAudio = () => {
  return (
    <>
      <Audio
        src={require('./assets/voiceover.mp3')}
        volume={(frame) => {
          // Fade in voiceover
          return interpolate(frame, [0, 30], [0, 1]);
        }}
      />
      <SceneContent />
    </>
  );
};
```

## Best Practices

### Component Organization

1. **Separate Concerns**:
   - Scenes in separate components
   - Reusable UI elements (buttons, cards, typography)
   - Constants and configuration in separate files
   - Data and content in structured format

2. **Naming Conventions**:
   - Component files: `SceneName.tsx`
   - Composition IDs: PascalCase (e.g., `ProductDemo`)
   - Constants: UPPER_SNAKE_CASE
   - Props: camelCase

3. **Type Safety**:
   - Use TypeScript for better maintainability
   - Define prop types for components
   - Validate data structures

### Animation Guidelines

1. **Frame-based Timing**:
   - Use `useCurrentFrame()` for frame-accurate timing
   - Avoid browser timers (`setTimeout`, `setInterval`)
   - Use Remotion's built-in timing utilities

2. **Deterministic Animation**:
   - Avoid `Math.random()` or `Date.now()`
   - Use seeded random if needed
   - Keep animations reproducible

3. **Performance**:
   - Test animations in Studio before final render
   - Use CSS transforms for GPU acceleration
   - Limit complex calculations per frame

### Text and Typography

1. **Readability**:
   - High contrast text (dark on light or light on dark)
   - Adequate font size (minimum 40px for mobile)
   - Generous line height (1.5x font size)
   - Safe margins (don't put text at edges)

2. **Fonts**:
   - Use web-safe fonts or embed custom fonts
   - Limit to 2-3 font families
   - Ensure fonts are loaded before rendering

3. **Captions**:
   - Use Remotion's text components for dynamic text
   - Implement text styling consistently
   - Consider accessibility (captions for audio)

### Asset Management

1. **Organization**:
   - Keep assets in `src/assets/` directory
   - Use subdirectories for different asset types
   - Reference assets through require() or import

2. **Optimization**:
   - Compress images before adding to project
   - Use appropriate formats (WebP for web, MP4 for video)
   - Consider sprite sheets for repeated elements

3. **External Assets**:
   - For large assets, consider hosting externally
   - Implement lazy loading if needed
   - Provide fallback for missing assets

## Debugging and Troubleshooting

### Common Issues

#### 1. Missing Browser or FFmpeg

**Error**: Render fails with browser or FFmpeg errors

**Solution**:
```bash
# Install Chrome
apt-get install -y google-chrome-stable

# Install FFmpeg
apt-get install -y ffmpeg

# Verify installation
google-chrome --version
ffmpeg -version
```

#### 2. Build Errors

**Error**: `npm run build` fails

**Solution**:
```bash
# Clean and rebuild
rm -rf node_modules
npm install
npm run build

# Check for TypeScript errors
npx tsc --noEmit

# Check for linting errors
npm run lint
```

#### 3. Render Failures

**Error**: Render command fails without clear message

**Solution**:
```bash
# Try rendering a still frame first
npx remotion still Scene1 --frame=30

# Check browser console in Studio
npx remotion studio

# Increase memory limit
NODE_OPTIONS=--max-old-space-size=4096 npx remotion render Scene1 out/video.mp4
```

#### 4. Layout Issues

**Symptom**: Elements appear in wrong positions

**Solution**:
- Use `npx remotion still Scene1 --scale=0.25 --frame=30` to inspect
- Check CSS positioning and layout
- Verify component structure
- Use browser dev tools in Studio preview

### Debugging Techniques

1. **Studio Preview**:
   ```bash
   npx remotion studio
   ```
   Use the built-in dev tools to inspect elements and debug animations.

2. **Still Frames**:
   ```bash
   npx remotion still Scene1 --frame=30 --scale=0.5
   ```
   Render specific frames to verify layout and styling.

3. **Console Logging**:
   ```tsx
   console.log('Frame:', frame, 'Progress:', progress);
   ```
   Use console logging in components for debugging.

4. **Error Boundaries**:
   ```tsx
   import { ErrorBoundary } from 'remotion';
   
   <ErrorBoundary component={ErrorFallback}>
     <MyComponent />
   </ErrorBoundary>
   ```
   Catch and display errors gracefully.

## Performance Optimization

### For Large Projects

1. **Component Reuse**:
   - Create reusable components for repeated elements
   - Use composition patterns (Scene → Sequence → Component)
   - Extract common logic into custom hooks

2. **Animation Optimization**:
   - Use CSS transforms instead of layout-affecting properties
   - Limit complex calculations per frame
   - Use GSAP or other performant animation libraries

3. **Asset Optimization**:
   - Compress images and videos
   - Use appropriate formats and quality levels
   - Implement lazy loading for off-screen elements

4. **Rendering Optimization**:
   - Use `--concurrency` flag for parallel rendering
   - Render in chunks for very large projects
   - Monitor memory usage and adjust accordingly

### Memory Management

```bash
# Increase Node.js memory limit
NODE_OPTIONS=--max-old-space-size=4096 npx remotion render Scene1 out/video.mp4

# For very large projects
NODE_OPTIONS=--max-old-space-size=8192 npx remotion render all out/
```

## Delivery

When delivering a Remotion project, include:

1. **Remotion Project Path** - The source code directory
2. **Rendered MP4 Path** - The final deliverable
3. **Composition ID(s)** - Used for rendering
4. **Preview Command** - `npx remotion studio`
5. **Assumptions Made** - Duration, aspect ratio, style, assets, etc.
6. **Next Steps** - How to edit or iterate on the project

## Use Cases by Category

### Marketing and Sales
- Product demos and feature highlights
- Pricing announcements
- Customer testimonials
- Brand storytelling

### Education and Tutorials
- Step-by-step tutorials
- Code walkthroughs
- API documentation with visuals
- Training videos

### Technical Content
- API documentation videos
- Code review walkthroughs
- Architecture explanations
- Data visualization

### Creative Projects
- Story-driven animations
- Motion graphics
- Abstract visualizations
- Generative art

## Alternatives

If Remotion is unsuitable:
- Use **HyperFrames** for HTML/CSS/JS-based compositions
- Use **Grok Image-to-Video** for quick prompt-driven animation
- Use **manual video editing** for complex post-production
- Use **video editing software** for traditional workflows

## References

- Remotion Official Documentation: https://www.remotion.dev/
- React Documentation: https://react.dev/
- TypeScript Documentation: https://www.typescriptlang.org/
- Video Style Guide: `references/video-style-guide.md`
- Troubleshooting Guide: `references/troubleshooting.md`
- Composition Template: `templates/remotion-composition.tsx`