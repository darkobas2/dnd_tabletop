"""Veo 3 prompt builder for animated VTT maps.

Generates structured prompts tuned for Google Veo 3, encoding the constraints
that make a video usable as a virtual-tabletop battlemap: locked top-down
camera, seamless ambient loop, no characters, even lighting, grid-friendly
composition.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox,
    QLineEdit, QPlainTextEdit, QCheckBox, QPushButton, QSpinBox, QGroupBox,
    QApplication, QFileDialog, QMessageBox, QScrollArea, QWidget,
)
from PySide6.QtCore import Qt
from pathlib import Path


SCENE_PRESETS = {
    "Tavern interior": "a bustling fantasy tavern interior, long wooden tables, mugs and plates, a stone hearth on one side, wooden barrels stacked against a wall, a bar counter, rugs on a plank floor",
    "Dungeon corridor": "a stone dungeon corridor, weathered flagstones, mossy walls, iron sconces, scattered bones and rubble, a heavy wooden door, narrow side passages",
    "Forest clearing": "a wild forest clearing, mossy ground with patches of grass and wildflowers, fallen logs, a ring of ancient trees with twisting roots, dappled light reaching the floor",
    "Cave interior": "a damp cave interior, jagged rock walls, stalactites, scattered crystals catching faint light, small pools of dark water, sandy and rocky floor",
    "Swamp": "a murky swamp, twisted mangrove roots, mossy stumps, stagnant pools of green-tinged water, lily pads, a rotting wooden walkway",
    "Town square": "a stone-paved town square, market stalls with cloth awnings, a central fountain, cobblestones, wooden carts, half-timbered buildings around the edges",
    "Ship deck": "the wooden deck of a sailing ship, planks worn smooth, coiled ropes, barrels and crates, the base of a mast, a wheel, railings on the sides",
    "Throne room": "a grand stone throne room, a raised dais with an ornate stone throne, banners hanging from the walls, polished marble floor with inlay patterns, columns, braziers",
    "Ruined castle": "a crumbling castle courtyard, broken stone walls, toppled columns, weeds growing between flagstones, scattered debris, an old well, remnants of a fountain",
    "Wizard tower": "the circular interior of a wizard's tower, wooden floor with arcane inlays, bookshelves lining curved walls, alchemy table with bottles and scrolls, a writing desk, a celestial globe",
    "Snowy clearing": "a snow-covered forest clearing, fresh untrampled powder, frosted pine trees on the edges, a frozen stream cutting through, jagged dark rocks poking up through the snow",
    "Desert ruins": "ancient sandstone ruins in a desert, broken columns half-buried in sand, weathered carvings, fallen capstones, scattered sun-bleached bones, dunes encroaching",
    "Underground river": "an underground river cavern, dark water cutting through rock, narrow stone banks on either side, glowing mushrooms on the walls, mineral deposits, a small dock",
    "Goblin camp": "a crude goblin camp on a dirt floor, tattered tents made of hide and bone, a central campfire with a spit, scattered bones and crude weapons, wooden palisade fragments",
    "Cathedral interior": "the nave of a ruined cathedral, broken pews scattered on a tiled floor, fragments of stained glass, a stone altar, fallen rubble, columns reaching toward a broken ceiling",
}


TIME_OF_DAY = {
    "Bright day": "bright midday lighting, soft top-down sunlight, warm tones, sharp gentle shadows",
    "Overcast day": "overcast diffuse daylight, soft flat shadows, cool grey tones",
    "Dusk": "dusk lighting, long warm orange-red highlights, deepening blue shadows, lanterns just starting to glow",
    "Night": "deep night lighting, cool blue ambient with localized warm lantern and torch pools, strong contrast between lit and shadowed areas",
    "Dawn": "dawn lighting, soft pink and golden highlights, long cool shadows, gentle mist near the ground",
    "Magical twilight": "magical twilight, purple and teal ambient gradient, glowing accents on key objects, no obvious sun direction",
}


WEATHER = {
    "Clear": "",
    "Light rain": "light rain falling steadily, small puddles forming on flat surfaces with subtle ripples",
    "Heavy rain": "heavy rain pouring down, puddles with active ripples, wet glistening surfaces, faint drifting mist",
    "Light fog": "thin low-lying fog drifting slowly across the ground",
    "Heavy fog": "thick atmospheric fog rolling slowly across the scene, partially obscuring the edges",
    "Snowfall": "gentle snow drifting down steadily, fresh flakes accumulating on surfaces",
    "Blizzard": "heavy windblown snow streaking across the scene, drifts building against obstacles",
    "Ash fall": "fine grey ash drifting down slowly from above, settling on every surface",
}


ANIMATED_ELEMENTS = [
    ("Flickering torches", "torches and braziers flickering with warm orange flame, casting subtle dancing light onto nearby surfaces"),
    ("Crackling fireplace", "a fireplace or hearth crackling with active flames, glowing embers underneath, faint heat shimmer rising"),
    ("Rising smoke", "thin wisps of smoke rising slowly and curling away from fire sources"),
    ("Floating embers", "tiny orange embers drifting upward and fading"),
    ("Rippling water surface", "the surface of standing water rippling gently, light glints catching the motion"),
    ("Flowing stream", "a stream of water flowing steadily in one direction, small eddies around rocks, foam streaks"),
    ("Lapping waves", "gentle waves lapping against the edges, foam advancing and retreating"),
    ("Waterfall", "a small waterfall pouring continuously down rock, white spray at the base, light mist drifting"),
    ("Drifting fog", "low fog drifting slowly across the ground in soft tendrils"),
    ("Falling leaves", "autumn leaves drifting down slowly and rotating as they fall, settling on surfaces"),
    ("Swaying foliage", "leaves and small branches swaying gently as if from a soft breeze"),
    ("Swaying grass", "tall grass blades swaying in slow waves"),
    ("Fireflies", "soft glowing fireflies drifting in lazy paths through the air, blinking gently"),
    ("Dust motes", "fine dust motes drifting slowly through shafts of light"),
    ("Magical particles", "small glowing magical particles drifting upward and fading, faint sparkles catching the air"),
    ("Glowing runes", "softly pulsing arcane runes carved into stone, brightness fading in and out gently"),
    ("Pulsing crystals", "embedded crystals glowing with a slow steady pulse"),
    ("Hanging banners", "cloth banners swaying gently as if from a faint draft"),
    ("Steam vents", "small jets of steam rising intermittently from cracks or pipes"),
    ("Drifting petals", "small flower petals drifting down through the air"),
    ("Lightning flashes", "occasional distant lightning briefly illuminating the scene from above"),
    ("Rain puddles rippling", "puddles on the ground rippling continuously from falling drops"),
]


ART_STYLES = {
    "Painterly fantasy": "richly detailed painterly fantasy art style, hand-painted look reminiscent of high-end D&D campaign maps, brush-textured surfaces, warm saturated palette",
    "Storybook illustration": "soft storybook illustration style, gentle lines, slightly stylized shapes, warm inviting palette",
    "Dark gritty realism": "dark gritty semi-realistic style, muted desaturated palette, heavy shadows, weathered textures",
    "Watercolor": "loose watercolor style, soft washes of color, organic edges, paper-grain texture",
    "Photorealistic": "photorealistic rendering, accurate materials and lighting, fine surface detail",
    "Ink and color": "ink-line illustration with color washes, visible inked outlines on shapes, flat color fills with subtle gradients",
}


ASPECT_RATIOS = ["16:9", "4:3", "1:1", "9:16"]


def _ffmpeg_upscale(src: str, dest: str, target_w: int = 1920, target_h: int = 1080):
    """Run ffmpeg to upscale src to target_w x target_h using lanczos.

    Returns (ok: bool, message: str). Preserves aspect via decrease-fit pad.
    """
    import subprocess, shutil as _sh
    ffmpeg = _sh.which("ffmpeg")
    if not ffmpeg:
        return False, "ffmpeg not found on PATH. Install ffmpeg to enable upscaling."

    # Scale to fit inside the target, then pad to exact dimensions so the
    # output is always exactly target_w x target_h.
    vf = (
        f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease:flags=lanczos,"
        f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:color=black"
    )
    cmd = [
        ffmpeg, "-y", "-i", src,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an",  # drop audio — VTT maps don't need it
        dest,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        return False, "ffmpeg timed out after 10 minutes."
    except OSError as e:
        return False, f"Failed to launch ffmpeg: {e}"

    if result.returncode != 0:
        tail = result.stderr.strip().splitlines()[-10:]
        return False, "ffmpeg exited with error:\n" + "\n".join(tail)
    return True, "ok"


def build_prompt(
    scene_label, scene_text,
    time_label, time_text,
    weather_label, weather_text,
    style_label, style_text,
    animated_elements,
    aspect_ratio,
    grid_w, grid_h,
    extra_notes,
):
    """Compose the final Veo 3 prompt from form inputs.

    The constraints are intentionally repeated under multiple headings. Veo
    weights repeated and emphasized instructions more heavily, and the goal
    here is a video that is *usable as a static battlemap*: the underlying
    map cannot drift, scroll, parallax, or rotate at any point.
    """

    parts = []

    parts.append(
        "[FORMAT] Pure top-down orthographic battlemap for a tabletop role-playing game. "
        "This is a FLAT 2D map illustration, NOT a 3D scene with perspective. "
        "Render it the way a printed Dungeons & Dragons battlemap, a Roll20 map tile, a Dyson Logos dungeon map, "
        "or a video game minimap looks: perfectly flat, viewed from directly overhead."
    )

    parts.append(
        "[PERSPECTIVE — STRICT] The camera angle is a 90-degree nadir shot — pointing straight down at the ground, "
        "perpendicular to the floor of the scene. "
        "There is ZERO tilt, ZERO oblique angle, ZERO perspective foreshortening, ZERO isometric projection. "
        "Vertical objects such as walls, columns, trees, and furniture are seen as their FOOTPRINTS — only their tops and bases are visible, "
        "with NO visible side walls, NO visible front faces, NO visible vertical surfaces extending toward or away from the viewer. "
        "The roof or top surface of every object faces the camera squarely. "
        "If you would normally see the side of an object from a high angle, you must NOT — only the top. "
        "Think of an architectural floor plan that has been beautifully painted: structures are represented purely by their plan view."
    )

    parts.append(
        "[SCENE] " + scene_text + ". "
        f"Composition fills a {aspect_ratio} frame. "
        f"The image will later have a {grid_w} by {grid_h} square grid overlaid programmatically by the virtual tabletop software — "
        "DO NOT draw, paint, etch, scratch, or otherwise include any grid in the video itself. "
        "Keep important features inset from the very edges so the external grid overlay does not crop anything important."
    )

    parts.append(
        "[LIGHTING] " + time_text + ". "
        "Lighting is flat, even, and consistent across the entire frame so every part of the map is clearly readable. "
        "Light sources do not move or change intensity over the duration of the clip. "
        "Shadows do not shift, rotate, or lengthen."
    )

    if weather_text:
        parts.append("[WEATHER] " + weather_text + ".")

    parts.append("[STYLE] " + style_text + ".")

    if animated_elements:
        elements_text = "; ".join(animated_elements)
    else:
        elements_text = "very subtle ambient environmental motion only (e.g. faint light flicker)"

    parts.append(
        "[ANIMATION] The only motion in the entire clip is small, localized, ambient environmental motion: "
        + elements_text + ". "
        "Everything else in the frame is perfectly still. "
        "The map terrain, walls, floors, furniture, props, rocks, trees, and structures do not move, drift, deform, or change shape at any point. "
        "No object enters or leaves the frame."
    )

    parts.append(
        "[CAMERA — CRITICAL] The camera is absolutely fixed and locked in a perfectly perpendicular top-down orthographic position for the entire clip. "
        "Camera pitch = -90 degrees (pointing straight down). Camera tilt = 0. Camera roll = 0. Camera yaw is irrelevant because the view is straight down. "
        "NO camera movement of any kind: no pan, no tilt, no roll, no yaw, no zoom-in, no zoom-out, no dolly, no truck, no crane, no orbit, no parallax, no handheld shake, no drift, no breathing, no rack focus, no depth-of-field change. "
        "The viewing angle stays exactly perpendicular to the ground (90 degrees nadir, straight down) from the first frame to the last frame. "
        "The framing, scale, position, and rotation of the map relative to the frame are pixel-identical in every frame. "
        "Treat the camera as if it were a fixed flatbed scanner pressed directly against the top of the scene. "
        "The map itself does not scroll, shift, slide, rotate, or reposition within the frame at any moment."
    )

    parts.append(
        "[LOOP] The clip must loop seamlessly. "
        "The final frame must be visually identical to the first frame in every pixel of the static (non-animated) areas. "
        "Animated elements should be at the same phase of their cycle at the start and end so the video can be played on repeat with no visible cut, jump, fade, or reset."
    )

    parts.append(
        "[EXCLUSIONS — STRICT] The clip must not contain any of the following under any circumstances: "
        "ANY tilted, oblique, isometric, axonometric, three-quarter, 3/4, high-angle, low-angle, or angled view — "
        "the camera is NEVER tilted off the strict vertical axis even by one degree, "
        "NO 3D perspective, NO vanishing points, NO foreshortening, NO depth cues from perspective, "
        "NO visible vertical walls or sides of objects, NO walls seen from the side, NO buildings shown with their facades, "
        "NO drone footage look, NO aerial cinematography look, NO Google Earth oblique view, "
        "people, humans, humanoids, characters, NPCs, player characters, adventurers, "
        "monsters, creatures, animals, insects, birds, fish moving through water, "
        "tokens, miniatures, figurines, dice, "
        "ANY visible grid, square grid, hex grid, hexagonal grid, grid lines, "
        "grid overlay, grid pattern, grid cells, checkerboard tiling, lattice, mesh, "
        "ruler markings, measurement overlays, scale bars, tick marks along edges, "
        "tile seams, repeating square or hex tile patterns visible across the floor, "
        "any text, letters, numbers, captions, subtitles, labels, place names, signage with readable text, "
        "any UI, HUD, watermarks, logos, brand marks, signatures, "
        "any camera movement or cinematic motion, "
        "any zoom, pan, tilt, dolly, push-in, pull-out, or close-up shot, "
        "any cut to a different shot or angle, "
        "any change in time of day, weather, or lighting mood mid-clip, "
        "any fade-in or fade-out at the start or end, "
        "any letterboxing, vignettes that change over time, or post-processing flicker."
    )

    parts.append(
        "[REMINDER] This is a static, perfectly flat, top-down battlemap with only minor ambient animation, with NO grid drawn on it. "
        "Imagine a printed paper map lying flat on a table, photographed from directly above with a fixed camera at exactly 90 degrees, "
        "where only natural ambient details such as flames, water surfaces, or drifting fog gently animate "
        "while every other pixel stays absolutely still. "
        "The surface of the map is a clean illustrated environment — no square or hex grid is painted, drawn, etched, or overlaid on it; "
        "the grid will be added later by external software. "
        "If you can see the side of a wall, or a building's facade, or any vertical surface, the angle is WRONG. "
        "You should only see floors, roofs, ground, and the tops of objects. "
        "The camera does not move. The map does not move. The angle does not change. "
        "Only the listed ambient elements move."
    )

    if extra_notes.strip():
        parts.append("[EXTRA DIRECTION] " + extra_notes.strip())

    return "\n\n".join(parts)


class VeoMapPromptDialog(QDialog):
    def __init__(self, parent=None, save_dir=None):
        super().__init__(parent)
        self.setWindowTitle("Veo 3 Animated Map Prompt Builder")
        self.resize(900, 720)
        self._save_dir = Path(save_dir) if save_dir else Path("map_library") / "_prompts"

        outer = QVBoxLayout(self)

        # Scrollable form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_host = QWidget()
        form = QVBoxLayout(form_host)

        # Scene group
        scene_group = QGroupBox("Scene")
        sg = QGridLayout(scene_group)
        sg.addWidget(QLabel("Scene type:"), 0, 0)
        self.scene_combo = QComboBox()
        self.scene_combo.addItems(SCENE_PRESETS.keys())
        sg.addWidget(self.scene_combo, 0, 1)

        sg.addWidget(QLabel("Time of day:"), 0, 2)
        self.time_combo = QComboBox()
        self.time_combo.addItems(TIME_OF_DAY.keys())
        sg.addWidget(self.time_combo, 0, 3)

        sg.addWidget(QLabel("Weather:"), 1, 0)
        self.weather_combo = QComboBox()
        self.weather_combo.addItems(WEATHER.keys())
        sg.addWidget(self.weather_combo, 1, 1)

        sg.addWidget(QLabel("Art style:"), 1, 2)
        self.style_combo = QComboBox()
        self.style_combo.addItems(ART_STYLES.keys())
        sg.addWidget(self.style_combo, 1, 3)

        sg.addWidget(QLabel("Aspect ratio:"), 2, 0)
        self.ratio_combo = QComboBox()
        self.ratio_combo.addItems(ASPECT_RATIOS)
        sg.addWidget(self.ratio_combo, 2, 1)

        sg.addWidget(QLabel("Grid (W x H):"), 2, 2)
        ratio_row = QHBoxLayout()
        self.grid_w = QSpinBox()
        self.grid_w.setRange(8, 80)
        self.grid_w.setValue(30)
        self.grid_h = QSpinBox()
        self.grid_h.setRange(8, 80)
        self.grid_h.setValue(20)
        ratio_row.addWidget(self.grid_w)
        ratio_row.addWidget(QLabel("x"))
        ratio_row.addWidget(self.grid_h)
        ratio_row.addStretch()
        ratio_host = QWidget()
        ratio_host.setLayout(ratio_row)
        sg.addWidget(ratio_host, 2, 3)

        form.addWidget(scene_group)

        # Animated elements
        anim_group = QGroupBox("Animated elements (pick a few — subtle is better than busy)")
        anim_layout = QGridLayout(anim_group)
        self.element_checks = []
        cols = 3
        for idx, (label, text) in enumerate(ANIMATED_ELEMENTS):
            cb = QCheckBox(label)
            cb.setToolTip(text)
            cb.stateChanged.connect(self._regenerate)
            self.element_checks.append((cb, text))
            anim_layout.addWidget(cb, idx // cols, idx % cols)
        form.addWidget(anim_group)

        # Extra notes
        extra_group = QGroupBox("Extra direction (optional)")
        extra_layout = QVBoxLayout(extra_group)
        self.extra_edit = QLineEdit()
        self.extra_edit.setPlaceholderText("e.g. blood splatter on the floor near the throne, autumn color palette, ...")
        self.extra_edit.textChanged.connect(self._regenerate)
        extra_layout.addWidget(self.extra_edit)
        form.addWidget(extra_group)

        form.addStretch()
        scroll.setWidget(form_host)
        outer.addWidget(scroll, 1)

        # Generated prompt
        outer.addWidget(QLabel("<b>Generated Veo 3 prompt:</b>"))
        self.prompt_view = QPlainTextEdit()
        self.prompt_view.setMinimumHeight(180)
        outer.addWidget(self.prompt_view, 1)

        # Actions
        btn_row = QHBoxLayout()
        self.copy_btn = QPushButton("Copy to clipboard")
        self.copy_btn.clicked.connect(self._copy)
        btn_row.addWidget(self.copy_btn)

        self.save_btn = QPushButton("Save as .txt")
        self.save_btn.clicked.connect(self._save)
        btn_row.addWidget(self.save_btn)

        self.import_btn = QPushButton("Import generated video...")
        self.import_btn.setStyleSheet(
            "QPushButton { background: #27ae60; color: white; font-weight: bold; padding: 4px 12px; border-radius: 4px; }"
            "QPushButton:hover { background: #2ecc71; }"
        )
        self.import_btn.setToolTip("Copy a Veo-generated .mp4/.webm into map_library/ (offers FHD upscale)")
        self.import_btn.clicked.connect(self._import_video)
        btn_row.addWidget(self.import_btn)

        self.upscale_btn = QPushButton("Upscale existing video to FHD...")
        self.upscale_btn.setStyleSheet(
            "QPushButton { background: #2980b9; color: white; font-weight: bold; padding: 4px 12px; border-radius: 4px; }"
            "QPushButton:hover { background: #3498db; }"
        )
        self.upscale_btn.setToolTip("Re-encode a video to 1920x1080 using ffmpeg (lanczos scaling)")
        self.upscale_btn.clicked.connect(self._upscale_video)
        btn_row.addWidget(self.upscale_btn)

        btn_row.addStretch()
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        btn_row.addWidget(self.close_btn)
        outer.addLayout(btn_row)

        # Wire all combos to regenerate
        for c in (self.scene_combo, self.time_combo, self.weather_combo,
                  self.style_combo, self.ratio_combo):
            c.currentIndexChanged.connect(self._regenerate)
        self.grid_w.valueChanged.connect(self._regenerate)
        self.grid_h.valueChanged.connect(self._regenerate)

        self._regenerate()

    def _regenerate(self):
        scene_label = self.scene_combo.currentText()
        time_label = self.time_combo.currentText()
        weather_label = self.weather_combo.currentText()
        style_label = self.style_combo.currentText()

        selected_elements = [text for cb, text in self.element_checks if cb.isChecked()]

        prompt = build_prompt(
            scene_label, SCENE_PRESETS[scene_label],
            time_label, TIME_OF_DAY[time_label],
            weather_label, WEATHER[weather_label],
            style_label, ART_STYLES[style_label],
            selected_elements,
            self.ratio_combo.currentText(),
            self.grid_w.value(),
            self.grid_h.value(),
            self.extra_edit.text(),
        )
        self.prompt_view.setPlainText(prompt)

    def _copy(self):
        QApplication.clipboard().setText(self.prompt_view.toPlainText())
        self.copy_btn.setText("Copied!")
        self.copy_btn.setEnabled(False)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1200, lambda: (self.copy_btn.setText("Copy to clipboard"), self.copy_btn.setEnabled(True)))

    def _save(self):
        self._save_dir.mkdir(parents=True, exist_ok=True)
        scene = self.scene_combo.currentText().lower().replace(" ", "_")
        time = self.time_combo.currentText().lower().replace(" ", "_")
        default_name = f"{scene}_{time}.txt"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Veo 3 prompt", str(self._save_dir / default_name), "Text (*.txt)"
        )
        if not path:
            return
        try:
            Path(path).write_text(self.prompt_view.toPlainText(), encoding="utf-8")
            QMessageBox.information(self, "Saved", f"Prompt saved to:\n{path}")
        except OSError as e:
            QMessageBox.warning(self, "Save failed", str(e))

    def _import_video(self):
        """Copy a Veo-generated .mp4/.webm into map_library/<category>/<name>."""
        import shutil
        src, _ = QFileDialog.getOpenFileName(
            self, "Pick Veo-generated video", "",
            "Video (*.mp4 *.webm)"
        )
        if not src:
            return

        # Suggest category folder based on the chosen scene
        scene_label = self.scene_combo.currentText()
        category_default = scene_label.split()[0].lower()
        library_root = Path("map_library")

        # Let the user choose / type the destination filename within the library
        ext = Path(src).suffix.lower()
        scene = scene_label.lower().replace(" ", "_")
        time = self.time_combo.currentText().lower().replace(" ", "_")
        weather = self.weather_combo.currentText().lower().replace(" ", "_")
        default_name = f"{scene}_{time}_{weather}{ext}"
        default_dest = str(library_root / category_default / default_name)

        dest, _ = QFileDialog.getSaveFileName(
            self, "Save into map library as", default_dest,
            "Video (*.mp4 *.webm)"
        )
        if not dest:
            return

        # Offer FHD upscale before copying
        do_upscale = QMessageBox.question(
            self, "Upscale to FHD?",
            "Re-encode the video to 1920x1080 using ffmpeg (lanczos)?\n\n"
            "Recommended for Veo 720p output. Adds 30s–2min depending on length.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        ) == QMessageBox.Yes

        try:
            Path(dest).parent.mkdir(parents=True, exist_ok=True)
            if do_upscale:
                ok, msg = _ffmpeg_upscale(src, dest)
                if not ok:
                    # Fall back to a plain copy and tell the user why
                    shutil.copy2(src, dest)
                    QMessageBox.warning(
                        self, "Upscale failed (file copied unscaled)", msg
                    )
            else:
                shutil.copy2(src, dest)
            # Also save the prompt alongside the video for traceability
            prompt_path = Path(dest).with_suffix(".prompt.txt")
            prompt_path.write_text(self.prompt_view.toPlainText(), encoding="utf-8")
            QMessageBox.information(
                self, "Imported",
                f"Video saved to:\n{dest}\n\nPrompt saved alongside as:\n{prompt_path.name}\n\n"
                "It should appear in the Map Library tab automatically."
            )
        except OSError as e:
            QMessageBox.warning(self, "Import failed", str(e))

    def _upscale_video(self):
        """Upscale any existing video to 1920x1080 via ffmpeg."""
        src, _ = QFileDialog.getOpenFileName(
            self, "Pick a video to upscale", "map_library",
            "Video (*.mp4 *.webm)"
        )
        if not src:
            return

        default_dest = str(Path(src).with_name(Path(src).stem + "_fhd.mp4"))
        dest, _ = QFileDialog.getSaveFileName(
            self, "Save upscaled video as", default_dest,
            "Video (*.mp4)"
        )
        if not dest:
            return

        ok, msg = _ffmpeg_upscale(src, dest)
        if ok:
            QMessageBox.information(self, "Upscaled", f"FHD video saved to:\n{dest}")
        else:
            QMessageBox.warning(self, "Upscale failed", msg)
