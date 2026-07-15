1|---
2|name: ai-video-generation
3|description: "Create AI videos with multiple approaches: xAI Grok Imagine image-to-video, HyperFrames HTML/CSS/JS compositions, and Remotion React-based video projects. Use for short videos, social media content, product demos, motion graphics, and code-based video iteration."
4|version: 2.0.0
5|author: Ekko
6|license: MIT
7|platforms: [linux, macos, windows]
8|metadata:
9|  hermes:
10|    tags: [ai-video, video-generation, media, xAI, Grokk, HyperFrames, Remotion]
11|prerequisites:
12|  commands: [node, npx, curl]
13|---
14|
15|# AI Video Generation
16|
17|Use this skill when the user wants to create a video using AI-powered tools. This umbrella skill provides three complementary approaches:
18|
19|1. **Grok Image-to-Video**: Animate a local image into a short video using xAI Grok Imagine via Hermes Web UI
20|2. **HyperFrames**: Create videos from HTML/CSS/JS compositions with GSAP animations
21|3. **Remotion**: Build editable React-based video projects with full control over timing and assets
22|
23|## Choosing the Right Approach
24|
25|| Approach | Best For | Requirements | Output | Editability |
26||----------|----------|--------------|--------|-------------|
27|| **Grok Image-to-Video** | Quick social media clips, cinematic effects from images | Hermes Web UI with xAI credentials, local image | MP4 | Low (regenerate) |
28|| **HyperFrames** | Motion graphics, HUD/tech visuals, web-to-video | Node.js, FFmpeg, HTML/CSS/JS skills | MP4 | Medium (edit HTML/CSS/JS) |
29|| **Remotion** | Product demos, tutorials, story-driven animations, reusable templates | Node.js, React skills, FFmpeg | MP4 | High (edit React components) |
30|
31|## Grok Image-to-Video (xAI Grok Imagine)
32|
32|For quick video generation from a static image:
33|
34|- **Input**: Local image file (PNG, JPEG, WebP)
35|- **Output**: MP4 video with cinematic motion
36|- **Use Case**: Social media clips, product previews, quick animations
37|- **Workflow**: Upload image, provide motion prompt, generate video
38|
39|See: `references/grok-image-to-video.md`
40|
41|## HyperFrames (HTML/CSS/JS Compositions)
41|
42|For motion graphics and web-to-video conversions:
43|
44|- **Input**: HTML/CSS/JS composition
45|- **Output**: MP4 video
46|- **Use Case**: HUD/tech visuals, subtitle animations, motion graphics, converting web content to video
47|- **Workflow**: Build composition, validate, preview, render
48|
49|See: `references/hyperframes-workflow.md`
50|
51|## Remotion (React-based Video Projects)
52|
53|For code-based video projects with maximum control:
54|
55|- **Input**: React components and assets
56|- **Output**: MP4 video
57|- **Use Case**: Product demos, tutorials, story-driven animations, reusable templates, code walkthroughs
58|- **Workflow**: Build React components, preview in Studio, render
59|
60|See: `references/remotion-workflow.md`
61|
62|## Getting Started
62|
63|### Quick Start (Grok Image-to-Video)
64|
65|```bash
66|# Ensure you have Hermes Web UI running with xAI credentials
67|
68|# Use the skill directly
69|hermes skills run ai-video-generation --image-path /path/to/image.png \\
70|  --prompt "Animate with cinematic push-in effect" \\
71|  --duration 8 \\
72|  --output /path/to/output.mp4
71|
72|```
73|
74|### HyperFrames Project
74|
75|```bash
76|# Initialize project
77|npx hyperframes init my-video --non-interactive
78|
79|# Edit src/index.html, styles.css, script.js
80|
81|# Validate
82|npx hyperframes lint
83|npx hyperframes inspect --samples 15
84|
85|# Preview
86|npx hyperframes preview
87|
88|# Render
89|npx hyperframes render --output final.mp4 --quality high
90|```
92|
93|### Remotion Project
94|
95|```bash
96|# Create project
97|npx create-video@latest --yes --blank --no-tailwind my-video
98|cd my-video
99|
100|# Edit src/components and src/composition.tsx
101|
102|# Preview
103|npx remotion studio
104|
105|# Render
106|npx remotion render main-composition out/final.mp4
107|```
108|
109|## Troubleshooting
110|
111|### Common Issues
112|
112|1. **Missing Dependencies**:
113|   - Ensure Node.js, npx, and required tools are installed
114|   - For Grok: Verify Hermes Web UI is running with xAI credentials
115|   - For HyperFrames/Remotion: Verify FFmpeg is installed
116|
117|2. **Authentication Errors**:
118|   - Grok Image-to-Video requires Hermes Web UI token and xAI credentials
119|   - Check token resolution order in `references/grok-image-to-video.md`
120|
121|3. **Render Failures**:
122|   - Run diagnostic commands: `npx hyperframes doctor` or `npx remotion --help`
123|   - Check browser and FFmpeg installations
124|   - Increase Node.js memory limit if needed
125|
126|4. **Layout Issues**:
127|   - Always validate with `lint` and `inspect` commands
128|   - Use preview servers to catch issues early
129|
130|## Best Practices
131|
132|### For All Approaches
133|
134|- **Start Small**: Begin with short videos (8-15 seconds) to validate the approach
135|- **Validate Early**: Use preview and validation commands before final rendering
136|- **Organize Assets**: Keep input/output files organized in a project directory
137|- **Document Assumptions**: Note duration, aspect ratio, style, and other parameters
138|
139|### Grok Image-to-Video
140|
141|- Be specific with motion prompts: "cinematic push-in", "subtle parallax", "camera orbit"
142|- Use absolute paths for input and output files
143|- Check xAI API rate limits and quotas
144|
145|### HyperFrames
146|
147|- Build static layout first, then add animation
148|- Use CSS as the final state, animate from/to that state
149|- Validate with `inspect` command at multiple timestamps
150|- Keep text readable on mobile devices
151|
152|### Remotion
153|
154|- Separate concerns: scenes in components, data in constants
155|- Use TypeScript for better maintainability
156|- Preview in Studio frequently during development
157|- Keep animations deterministic and reproducible
158|
159|## Delivery Checklist
160|
161|When delivering a video project, ensure you have:
162|
161|1. ✅ Rendered MP4 file(s)
162|2. ✅ Source project files (if user wants to edit)
163|3. ✅ Preview command or Studio URL
164|4. ✅ Composition ID(s) used for rendering
165|5. ✅ Documentation of assumptions (duration, aspect ratio, style, assets)
166|6. ✅ Validation results (any issues found and addressed)
167|7. ✅ Instructions for iteration or modification
168|
169|## References
170|
171|- Grok Image-to-Video: `references/grok-image-to-video.md`
172|- HyperFrames Workflow: `references/hyperframes-workflow.md`
173|- Remotion Workflow: `references/remotion-workflow.md`
174|- Video Style Guide: `references/video-style-guide.md`
175|- Troubleshooting Guide: `references/troubleshooting.md`
176|
177|## Examples
178|
178|### Example 1: Grok Image-to-Video
179|
180|User request: "Create a 10-second video from my product photo with a cinematic push-in effect"
181|
182|Approach: Grok Image-to-Video
183|
184|```bash
185|# Hermes Web UI handles the xAI integration
186|# User provides image and prompt
187|```
188|
189|### Example 2: HyperFrames Motion Graphics
189|
190|User request: "Create a 15-second vertical video with animated title and logo for my product"
191|
192|Approach: HyperFrames
193|
194|```bash
195|# Build HTML/CSS/JS composition
196|# Use GSAP for smooth animations
197|# Validate and render
198|```
199|
200|### Example 3: Remotion Product Demo
201|
201|User request: "Create a 60-second tutorial video showing how to use my API with code examples"
202|
203|Approach: Remotion
204|
205|```bash
206|# Create React components for each scene
207|# Add code syntax highlighting
208|# Include voiceover and captions
209|# Preview and render final video
210|```
211|
212|---
213|
214|**Note**: This skill orchestrates three distinct video generation approaches. Always choose the approach that best fits the user's requirements, skills, and project constraints.