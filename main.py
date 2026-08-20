# 1: IMPORTS, CONSTANTS & HELPER FUNCTIONS
import asyncio
import pygame
from arrowSequence import arrow_sequence

# Constant Definitions
W, H = 1200, 600
RES = W, H
TEMPO = 132
LATENCY_BEAT_OFFSET = -1.5
MAX_ARROW_Y_DIST = 28
MISS_THRESHOLD_BEATS = 0.75
MAX_HEALTH = 100

arrowStart_x = 400
arrowSpacing = 100
arrowStart_y = 50

KEY_MAP = {
    pygame.K_LEFT: "L",
    pygame.K_DOWN: "D",
    pygame.K_UP: "U",
    pygame.K_RIGHT: "R"
}

# Helper Functions
def get_tinted_surface(surface, color):
    tinted = surface.copy()
    tinted.fill(color, special_flags=pygame.BLEND_RGBA_MULT)
    return tinted

def apply_hue_shift_fast(surface, percent):
    hue_deg = percent * 120.0
    c = pygame.Color(0)
    c.hsva = (hue_deg, 100, 100, 100)

    tinted = surface.copy()
    color_surface = pygame.Surface(tinted.get_size(), pygame.SRCALPHA)
    color_surface.fill((c.r, c.g, c.b, 255))

    tinted.blit(color_surface, (0, 0), special_flags=pygame.BLEND_ADD)
    alpha_mask = surface.copy()
    tinted.blit(alpha_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return tinted

# 2: CLASS DEFINITIONS (OUTSIDE MAIN)
class GrayArrow:
    def __init__(self, x, y, direction, base_img):
        self.x = x
        self.y = y
        self.direction = direction  
        self.size = 80
        self.rect = pygame.Rect(self.x, self.y, int(self.size * 1.1), self.size)
        scaled_image = pygame.transform.scale(base_img, (int(self.size * 1.1), self.size))
        self.image = self.rotate_arrow(scaled_image)

    def rotate_arrow(self, img):
        if self.direction == "L":
            return pygame.transform.rotate(img, 180)
        elif self.direction == "D":
            return pygame.transform.rotate(img, -90)
        elif self.direction == "U":
            return pygame.transform.rotate(img, 90)
        return img  

    def draw(self, surface):
        surface.blit(self.image, self.rect)

class Arrow(GrayArrow):
    def __init__(self, direction, target_beat, base_img, pixels_per_beat):
        directions = ["L", "D", "U", "R"]
        i = directions.index(direction)
        start_x = arrowStart_x + (i * arrowSpacing)
        
        super().__init__(start_x, H, direction, base_img)
        
        self.pixels_per_beat = pixels_per_beat
        self.target_beat = target_beat
        self.is_fading = False
        self.alpha = 255
        self.brightness = 0

        color_map = {
            "L": (255, 50, 50, 255),
            "D": (255, 255, 50, 255),
            "U": (0, 255, 50, 255),
            "R": (100, 120, 250, 255)
        }
        target_color = color_map[self.direction]
        self.image = get_tinted_surface(self.image, target_color)

    def update(self, current_beat):
        if self.is_fading:
            self.alpha -= 30
            if self.alpha <= 0:
                self.alpha = 0
            self.image.set_alpha(self.alpha)

            self.brightness += 51
            if self.brightness > 255:
                self.brightness = 255
        else:
            self.y = arrowStart_y + (self.target_beat - current_beat) * self.pixels_per_beat
            self.rect.y = int(self.y)

    def draw(self, surface):
        if self.is_fading and self.brightness > 0:
            bright_image = self.image.copy()
            b = int(self.brightness)
            bright_image.fill((b, b, b), special_flags=pygame.BLEND_RGB_ADD)
            surface.blit(bright_image, self.rect)
        else:
            surface.blit(self.image, self.rect)

class HealthBar:
    def __init__(self, x, y, base_path="images/Base.png", empty_path="images/Empty.png", full_path="images/Full.png"):
        self.x = x
        self.y = y

        self.base_img = pygame.transform.rotate(pygame.image.load(base_path).convert_alpha(), 90)
        self.empty_img = pygame.transform.rotate(pygame.image.load(empty_path).convert_alpha(), 90)
        self.full_img = pygame.transform.rotate(pygame.image.load(full_path).convert_alpha(), 90)

        self.width = self.base_img.get_width()
        self.height = self.base_img.get_height()

    def draw(self, surface, current_health, max_health):
        percent = current_health / max_health if max_health > 0 else 0
        percent = max(0.0, min(1.0, percent))

        tinted_base = apply_hue_shift_fast(self.base_img, percent)
        surface.blit(tinted_base, (self.x, self.y))

        if percent > 0.5:
            full_bracket_pct = (percent - 0.5) / 0.5
            f_w = self.full_img.get_width()
            f_h = self.full_img.get_height()
            visible_height = int(f_h * full_bracket_pct)

            if visible_height > 0:
                crop_rect = pygame.Rect(0, f_h - visible_height, f_w, visible_height)
                sub_surface = self.full_img.subsurface(crop_rect)
                tinted_sub = apply_hue_shift_fast(sub_surface, percent)

                y_offset = 5
                draw_y = self.y + (f_h - visible_height) + y_offset
                surface.blit(tinted_sub, (self.x, draw_y))
        else:
            empty_bracket_pct = 1.0 - (percent / 0.5)
            e_w = self.empty_img.get_width()
            e_h = self.empty_img.get_height()
            visible_height = int(e_h * empty_bracket_pct)

            if visible_height > 0:
                crop_rect = pygame.Rect(0, 0, e_w, visible_height)
                sub_surface = self.empty_img.subsurface(crop_rect)
                tinted_empty = apply_hue_shift_fast(sub_surface, percent)
                surface.blit(tinted_empty, (self.x, self.y + (self.height // 2)))

class Comment:
    def __init__(self, text, color, x=200, y=300):
        self.text = text
        self.color = color
        self.x = x
        self.y = y
        self.alpha = 255
        self.font = pygame.font.SysFont("Arial", 36, bold=True)
        
    def update(self):
        self.y -= 3 
        self.alpha -= 8
        if self.alpha < 0:
            self.alpha = 0
            
    def draw(self, surface):
        if self.alpha > 0:
            text_surface = self.font.render(self.text, True, self.color)
            text_with_alpha = text_surface.copy()
            text_with_alpha.set_alpha(self.alpha)
            rect = text_with_alpha.get_rect(center=(self.x, int(self.y)))
            surface.blit(text_with_alpha, rect)

class CommentManager:
    def __init__(self):
        self.active_comments = []

    def add_comment(self, hit_dist):
        if hit_dist <= 2:
            comment = Comment("Perfect!!!!!", (50, 255, 55))
        elif hit_dist <= 5:
            comment = Comment("Awesome!!!!", (50, 255, 255))
        elif hit_dist <= 9:
            comment = Comment("Great!!!", (255, 255, 50))
        elif hit_dist <= 15:
            comment = Comment("Nice!!", (155, 255, 50))
        elif hit_dist <= 22:
            comment = Comment("Good!", (220, 255, 10))
        else:
            comment = Comment("Bad", (255, 100, 50))
        self.active_comments.append(comment)

    def add_miss(self):
        comment = Comment("Miss...", (255, 50, 50))
        self.active_comments.append(comment)

    def update_and_draw(self, surface):
        for comment in self.active_comments[:]:
            comment.update()
            comment.draw(surface)
            if comment.alpha <= 0:
                self.active_comments.remove(comment)

# 3: ASYNC MAIN RUNTIME (PYGAME INIT, INSTANTIATION & GAME LOOP)
async def main():
    # Dynamic Game Variables
    Score = 0
    health = 100
    gameOver = False
    songComplete = False
    fade_alpha = 0
    fade_speed = 5

    music_fading = False
    music_fade_start = 0
    music_fade_duration = 0

    # 1. Initialize Pygame Modules
    pygame.init()
    pygame.mixer.init()
    pygame.font.init()

    screen = pygame.display.set_mode(RES)
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("Arial", 30)
    score_font = pygame.font.SysFont("Arial", 48, bold=True)

    # 2. Load Assets
    bgimage = pygame.image.load("images/bg.jpg")
    gArrow = pygame.image.load("images/GreyArrow.png")

    scale_ratio = W / bgimage.get_width()
    new_height = int(bgimage.get_height() * scale_ratio)
    bgimage = pygame.transform.scale(bgimage, (W, new_height))

    game_over_img = pygame.transform.scale(pygame.image.load("images/GameOver.png").convert_alpha(), (W, H))
    song_complete_img = pygame.transform.scale(pygame.image.load("images/SongComplete.png").convert_alpha(), (W, H))

    # 3. Chart Setup & Calculations
    travel_duration_seconds = 2.0
    beatsToTravel = travel_duration_seconds * (TEMPO / 60.0)
    travel_distance = H - arrowStart_y
    pixels_per_beat = travel_distance / beatsToTravel

    song_chart = []
    for direction, tapBeat in arrow_sequence:
        spawn_beat = tapBeat - beatsToTravel + LATENCY_BEAT_OFFSET
        song_chart.append((direction, spawn_beat, tapBeat))

    # 4. Instantiate Objects
    ui_health_bar = HealthBar(1000, 50)

    target_arrows = []
    directions = ["L", "D", "U", "R"]
    for i, dir_name in enumerate(directions):
        x_pos = arrowStart_x + (i * arrowSpacing)
        target = GrayArrow(x_pos, arrowStart_y, dir_name, gArrow)
        target_arrows.append(target)

    activeArrows = []
    comment_manager = CommentManager()

    # 5. Start Audio
    pygame.mixer.music.load("music/The Sky High.mp3")
    pygame.mixer.music.play(0)
    pygame.mixer.music.set_volume(0.8)
    missSFX = pygame.mixer.Sound("music/fnf-miss.wav")
    missSFX.set_volume(0.8)

    # 6. Main Async Game Loop
    running = True
    while running:
        # Event Processing
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.KEYDOWN and not (gameOver or songComplete):
                if event.key in KEY_MAP:
                    pressed_key_dir = KEY_MAP[event.key]
                    matching_arrows = [a for a in activeArrows if a.direction == pressed_key_dir and not a.is_fading]

                    if matching_arrows:
                        closest_arrow = min(matching_arrows, key=lambda a: abs(a.rect.y - arrowStart_y))
                        hit_dist = abs(closest_arrow.rect.y - arrowStart_y)

                        if hit_dist <= MAX_ARROW_Y_DIST:
                            closest_arrow.is_fading = True
                            closest_arrow.rect.y = arrowStart_y
                            Score += (MAX_ARROW_Y_DIST - hit_dist) * 10
                            health = min(MAX_HEALTH, health + 1)
                            comment_manager.add_comment(hit_dist)
                        else:
                            missSFX.play()
                            comment_manager.add_miss()
                            health = max(0, health - 4)

        # Audio Synchronization
        music_pos = pygame.mixer.music.get_pos()
        current_time_seconds = max(0.0, music_pos / 1000.0)
        current_beat = current_time_seconds * (TEMPO / 60.0)

        # Game State Checks
        if health <= 0 and not gameOver:
            gameOver = True
            music_fading = True
            music_fade_start = pygame.time.get_ticks()
            music_fade_duration = 2000

        no_more_arrows_to_spawn = len(song_chart) == 0

        if (no_more_arrows_to_spawn and len(activeArrows) == 0 and not gameOver and not songComplete):
            songComplete = True
            music_fading = True
            music_fade_start = pygame.time.get_ticks()
            music_fade_duration = 18000

        # Music Fade logic
        if music_fading:
            elapsed = pygame.time.get_ticks() - music_fade_start
            progress = min(elapsed / music_fade_duration, 1.0)
            volume = 0.8 * (1.0 - progress)
            pygame.mixer.music.set_volume(volume)

            if progress >= 1.0:
                pygame.mixer.music.stop()
                music_fading = False

        # Spawning Logic
        for i in range(len(song_chart) - 1, -1, -1):
            direction, spawn_beat, tap_beat = song_chart[i]
            if current_beat >= spawn_beat:
                new_arrow = Arrow(direction, tap_beat, gArrow, pixels_per_beat)
                activeArrows.append(new_arrow)
                song_chart.pop(i)

        # Update Active Arrows
        for i in range(len(activeArrows) - 1, -1, -1):
            arrow = activeArrows[i]
            arrow.update(current_beat)
            
            if not arrow.is_fading and not (gameOver or songComplete):
                if current_beat > (arrow.target_beat + MISS_THRESHOLD_BEATS):
                    comment_manager.add_miss()
                    missSFX.play()
                    health = max(0, health - 4)
                    activeArrows.pop(i)
                    continue

            if arrow.is_fading and arrow.alpha <= 0:
                activeArrows.pop(i)

        # Render Phase
        screen.fill((0, 0, 0))
        screen.blit(bgimage, (0, 0))

        for target in target_arrows:
            target.draw(screen)

        for arrow in activeArrows:
            arrow.draw(screen)

        ui_health_bar.draw(screen, health, MAX_HEALTH)

        if not (gameOver or songComplete): 
            comment_manager.update_and_draw(screen)

        # Beat Visualizer
        beat_fraction = current_beat % 1.0
        indicator_radius = int(35 - (beat_fraction * 25))
        brightness = int(255 * (1.0 - beat_fraction))
        indicator_color = (brightness, brightness, brightness)
        
        pygame.draw.circle(screen, indicator_color, (100, 80), indicator_radius)
        pygame.draw.circle(screen, (150, 150, 150), (100, 80), 35, 2)

        beat_text = font.render(f"Beat: {current_beat:.2f}", True, (255, 255, 255))
        screen.blit(beat_text, (50, 130))

        # Game Over / Completion Overlay
        if gameOver or songComplete:
            end_img = game_over_img if gameOver else song_complete_img

            if fade_alpha < 255:
                fade_alpha = min(255, fade_alpha + fade_speed)

            overlay = end_img.copy()
            overlay.set_alpha(fade_alpha)
            screen.blit(overlay, (0, 0))

            if fade_alpha >= 255:
                score_surface = score_font.render(f"Final Score: {Score}", True, (255, 255, 255))
                score_rect = score_surface.get_rect(center=(screen.get_width() // 2, 450))

                shadow_surface = score_font.render(f"Final Score: {Score}", True, (0, 0, 0))
                screen.blit(shadow_surface, (score_rect.x + 2, score_rect.y + 2))
                screen.blit(score_surface, score_rect)

        pygame.display.flip()
        clock.tick(60)

        # CRITICAL FOR PYGBAG / BROWSER RUNTIME:
        await asyncio.sleep(0)

    pygame.quit()

# 4: SCRIPT LAUNCHER
asyncio.run(main())