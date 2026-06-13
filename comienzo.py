"""
Arena 3D - Shooter en Python
Requiere: pip install pygame
Ejecutar: python shooter.py

Controles:
  WASD       - Moverse
  Raton      - Apuntar (izq/der)
  Clic izq   - Disparar
  ESC        - Salir
"""

import pygame
import math
import random
import sys
import time

# ─────────────────────────────────────────────
#  CONFIGURACION
# ─────────────────────────────────────────────
W, H       = 1024, 600
FOV        = math.pi / 3          # 60°
HALF_FOV   = FOV / 2
NUM_RAYS   = W // 2
MAX_DEPTH  = 20
DELTA_ANGLE= FOV / NUM_RAYS
SCALE      = W // NUM_RAYS
PLAYER_SPD = 3.5
TURN_SPD   = 0.0015
FPS        = 60

# Colores
BLACK   = (0,   0,   0)
WHITE   = (255, 255, 255)
GREY    = (100, 100, 100)
DKGREY  = (30,  30,  40)
RED     = (200, 30,  30)
ORANGE  = (249, 115, 22)
YELLOW  = (255, 220, 50)
GREEN   = (60,  200, 80)
BLUE    = (30,  80,  200)
PINK    = (200, 50,  150)
SKY     = (10,  10,  25)
FLOOR   = (18,  18,  30)
WALL_B  = (40,  40,  70)
WALL_D  = (20,  20,  50)
HUD_BG  = (0,   0,   0,  140)

# ─────────────────────────────────────────────
#  MAPA  (1=pared, 0=libre)
# ─────────────────────────────────────────────
MAP_W, MAP_H = 20, 20
RAW_MAP = [
    "####################",
    "#..................#",
    "#..###.......###..#",
    "#..#...........#..#",
    "#..#....###....#..#",
    "#.......#.#.......#",
    "#..##...###...##..#",
    "#..#...........#..#",
    "#..................#",
    "#....####.####....#",
    "#....#......#.....#",
    "#....#......#.....#",
    "#....########.....#",
    "#..................#",
    "#..##.......##....#",
    "#..#.........#....#",
    "#..#.........#....#",
    "#..###.....###....#",
    "#..................#",
    "####################",
]
MAP = [[1 if c == '#' else 0 for c in row] for row in RAW_MAP]

def is_wall(x, y):
    mx, my = int(x), int(y)
    if 0 <= mx < MAP_W and 0 <= my < MAP_H:
        return MAP[my][mx] == 1
    return True

# ─────────────────────────────────────────────
#  CLASES
# ─────────────────────────────────────────────

class Player:
    def __init__(self):
        self.x     = 3.5
        self.y     = 3.5
        self.angle = 0.0
        self.hp    = 100
        self.max_hp= 100
        self.speed = PLAYER_SPD
        self.score = 0
        self.damage_flash = 0  # frames de rojo en pantalla

    def take_damage(self, dmg):
        self.hp = max(0, self.hp - dmg)
        self.damage_flash = 12

    def move(self, keys, dt):
        sin_a = math.sin(self.angle)
        cos_a = math.cos(self.angle)
        spd = self.speed * dt

        dx = dy = 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dx += cos_a; dy += sin_a
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dx -= cos_a; dy -= sin_a
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx += sin_a; dy -= cos_a
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx -= sin_a; dy += cos_a

        length = math.hypot(dx, dy)
        if length:
            dx /= length; dy /= length

        nx = self.x + dx * spd
        ny = self.y + dy * spd
        if not is_wall(nx, self.y): self.x = nx
        if not is_wall(self.x, ny): self.y = ny

        if self.damage_flash > 0:
            self.damage_flash -= 1


class Bullet:
    SPEED = 12.0

    def __init__(self, x, y, angle):
        self.x     = x
        self.y     = y
        self.angle = angle
        self.dx    = math.cos(angle) * self.SPEED
        self.dy    = math.sin(angle) * self.SPEED
        self.alive = True
        self.dist  = 0.0

    def update(self, dt):
        self.x    += self.dx * dt
        self.y    += self.dy * dt
        self.dist += self.SPEED * dt
        if is_wall(self.x, self.y) or self.dist > 15:
            self.alive = False


class Enemy:
    TYPES = {
        'normal': dict(color=PINK,   hp=40,  speed=1.8, size=0.35, pts=50,  dmg=12),
        'fast':   dict(color=ORANGE, hp=20,  speed=3.2, size=0.25, pts=80,  dmg=8),
        'heavy':  dict(color=RED,    hp=100, speed=1.0, size=0.50, pts=150, dmg=20),
    }

    def __init__(self, x, y, etype='normal'):
        cfg        = self.TYPES[etype]
        self.x     = x
        self.y     = y
        self.etype = etype
        self.color = cfg['color']
        self.hp    = cfg['hp']
        self.max_hp= cfg['hp']
        self.speed = cfg['speed']
        self.size  = cfg['size']
        self.pts   = cfg['pts']
        self.dmg   = cfg['dmg']
        self.alive = True
        self.phase = random.uniform(0, math.pi*2)

    def update(self, player, dt):
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)
        if dist < 0.01:
            return dist
        nx = self.x + (dx/dist) * self.speed * dt
        ny = self.y + (dy/dist) * self.speed * dt
        if not is_wall(nx, self.y): self.x = nx
        if not is_wall(self.x, ny): self.y = ny
        return dist


class Particle:
    def __init__(self, x, y, color):
        self.x     = x
        self.y     = y
        self.color = color
        angle      = random.uniform(0, math.pi*2)
        speed      = random.uniform(1, 4)
        self.vx    = math.cos(angle)*speed
        self.vy    = math.sin(angle)*speed
        self.life  = random.randint(20, 40)
        self.alive = True

    def update(self):
        self.x    += self.vx * 0.05
        self.y    += self.vy * 0.05
        self.vx   *= 0.92
        self.vy   *= 0.92
        self.life -= 1
        if self.life <= 0:
            self.alive = False


# ─────────────────────────────────────────────
#  RAYCASTING
# ─────────────────────────────────────────────

def cast_rays(surface, player):
    """Devuelve lista de (ray_angle, perp_dist) para sprites."""
    ray_angle = player.angle - HALF_FOV
    depth_buf  = []

    for ray in range(NUM_RAYS):
        sin_a = math.sin(ray_angle)
        cos_a = math.cos(ray_angle)

        # DDA
        for depth in range(1, MAX_DEPTH * 10):
            d = depth * 0.05
            tx = player.x + cos_a * d
            ty = player.y + sin_a * d
            if is_wall(tx, ty):
                break

        # Corregir distorsion de ojo de pez
        depth = d * math.cos(player.angle - ray_angle)
        depth = max(depth, 0.001)
        depth_buf.append(depth)

        # Altura de la pared
        wall_h = min(int(H / depth), H)
        wall_top    = H // 2 - wall_h // 2
        wall_bottom = wall_top + wall_h

        # Shade por distancia
        shade = max(30, 255 - int(depth * 18))
        color_b = (
            int(WALL_B[0] * shade / 255),
            int(WALL_B[1] * shade / 255),
            int(WALL_B[2] * shade / 255),
        )

        pygame.draw.rect(surface, color_b,
                         (ray * SCALE, wall_top, SCALE, wall_h))
        ray_angle += DELTA_ANGLE

    return depth_buf


# ─────────────────────────────────────────────
#  SPRITES (enemigos en pantalla)
# ─────────────────────────────────────────────

def draw_sprites(surface, player, enemies, depth_buf):
    """Proyecta enemigos como billboards."""
    sprites = []
    for e in enemies:
        if not e.alive:
            continue
        dx = e.x - player.x
        dy = e.y - player.y
        dist = math.hypot(dx, dy)
        if dist < 0.1:
            continue

        # Angulo relativo al jugador
        angle = math.atan2(dy, dx) - player.angle
        # Normalizar al rango [-pi, pi]
        while angle < -math.pi: angle += 2*math.pi
        while angle >  math.pi: angle -= 2*math.pi

        if abs(angle) > HALF_FOV + 0.2:
            continue

        # Posicion en pantalla
        screen_x = int((angle / FOV + 0.5) * W)
        sprite_h = min(int(H / (dist + 0.0001)), H)
        sprite_w = sprite_h

        top  = H//2 - sprite_h//2
        left = screen_x - sprite_w//2

        # Cuerpo
        shade = max(40, 200 - int(dist*20))
        sc = tuple(int(c*shade/200) for c in e.color)

        # Dibuja pixel a pixel respetando depth buffer
        for col in range(sprite_w):
            ray_idx = (left + col) // SCALE
            if ray_idx < 0 or ray_idx >= NUM_RAYS:
                continue
            if dist < depth_buf[ray_idx]:
                pygame.draw.line(surface, sc,
                                 (left+col, top),
                                 (left+col, top+sprite_h))

        # Barra de vida encima
        if dist < 6:
            bar_w = max(20, sprite_w)
            bar_x = screen_x - bar_w//2
            bar_y = top - 8
            pygame.draw.rect(surface, (80,0,0),    (bar_x, bar_y, bar_w, 4))
            pygame.draw.rect(surface, (0,200,60),  (bar_x, bar_y, int(bar_w * e.hp/e.max_hp), 4))

        sprites.append((dist, e))

    return sprites


# ─────────────────────────────────────────────
#  HUD
# ─────────────────────────────────────────────

def draw_hud(surface, player, wave, kill_msgs, font_big, font_sm, font_tiny):
    sw, sh = surface.get_size()

    # ── Barra de salud ──
    bar_w, bar_h = 180, 14
    bx, by = 16, 16
    pygame.draw.rect(surface, (60,0,0),   (bx, by, bar_w, bar_h))
    hp_pct  = player.hp / player.max_hp
    hp_col  = GREEN if hp_pct > 0.5 else YELLOW if hp_pct > 0.25 else RED
    pygame.draw.rect(surface, hp_col, (bx, by, int(bar_w*hp_pct), bar_h))
    pygame.draw.rect(surface, WHITE,  (bx, by, bar_w, bar_h), 1)
    txt = font_tiny.render(f"SALUD  {int(player.hp)}", True, WHITE)
    surface.blit(txt, (bx+4, by-1))

    # ── Oleada ──
    wtxt = font_big.render(f"OLEADA  {wave}", True, ORANGE)
    surface.blit(wtxt, (sw//2 - wtxt.get_width()//2, 10))

    # ── Puntos ──
    stxt = font_sm.render(f"PUNTOS: {player.score}", True, YELLOW)
    surface.blit(stxt, (sw - stxt.get_width() - 16, 16))

    # ── Mira ──
    cx, cy = sw//2, sh//2
    pygame.draw.line(surface, WHITE, (cx-12, cy), (cx-4, cy), 2)
    pygame.draw.line(surface, WHITE, (cx+4,  cy), (cx+12, cy), 2)
    pygame.draw.line(surface, WHITE, (cx, cy-12), (cx, cy-4), 2)
    pygame.draw.line(surface, WHITE, (cx, cy+4),  (cx, cy+12), 2)
    pygame.draw.circle(surface, WHITE, (cx, cy), 3, 1)

    # ── Kill feed ──
    for i, (msg, alpha, col) in enumerate(kill_msgs):
        km = font_tiny.render(msg, True, col)
        surface.blit(km, (sw - km.get_width() - 16, 50 + i*20))

    # ── Flash de daño ──
    if player.damage_flash > 0:
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        a = int(140 * player.damage_flash / 12)
        overlay.fill((200, 0, 0, a))
        surface.blit(overlay, (0, 0))


def draw_minimap(surface, player, enemies, mm_x=16, mm_y=450, scale=8):
    size = MAP_W * scale
    mm   = pygame.Surface((size, size), pygame.SRCALPHA)
    mm.fill((0, 0, 0, 120))
    for my in range(MAP_H):
        for mx in range(MAP_W):
            if MAP[my][mx]:
                pygame.draw.rect(mm, (80,80,120), (mx*scale, my*scale, scale-1, scale-1))
    # Jugador
    px = int(player.x * scale)
    py = int(player.y * scale)
    pygame.draw.circle(mm, GREEN, (px, py), 3)
    # Dirección
    ex = px + int(math.cos(player.angle)*6)
    ey = py + int(math.sin(player.angle)*6)
    pygame.draw.line(mm, GREEN, (px, py), (ex, ey), 2)
    # Enemigos
    for e in enemies:
        if e.alive:
            pygame.draw.circle(mm, RED, (int(e.x*scale), int(e.y*scale)), 2)
    pygame.draw.rect(mm, WHITE, (0, 0, size, size), 1)
    surface.blit(mm, (mm_x, mm_y))


# ─────────────────────────────────────────────
#  SPAWNER DE OLEADAS
# ─────────────────────────────────────────────

SPAWN_POINTS = [
    (1.5,1.5),(18.5,1.5),(1.5,18.5),(18.5,18.5),
    (10,1.5),(1.5,10),(18.5,10),(10,18.5),
    (5,15),(15,5),(15,15),(5,5),
]

def spawn_wave(wave_num):
    enemies  = []
    count    = 4 + wave_num * 2
    etype_pool = (['normal']*3 + ['fast']*(1 if wave_num<3 else 2)
                  + ['heavy']*(0 if wave_num<2 else 1))
    pts  = random.sample(SPAWN_POINTS, min(count, len(SPAWN_POINTS)))
    for i in range(count):
        sp    = pts[i % len(pts)]
        jx    = sp[0] + random.uniform(-0.5, 0.5)
        jy    = sp[1] + random.uniform(-0.5, 0.5)
        etype = random.choice(etype_pool)
        enemies.append(Enemy(jx, jy, etype))
    return enemies


# ─────────────────────────────────────────────
#  PANTALLAS
# ─────────────────────────────────────────────

def screen_intro(surface, font_big, font_sm, font_tiny):
    surface.fill(BLACK)
    t1 = font_big.render("⚔  ARENA 3D", True, ORANGE)
    t2 = font_sm.render("WASD / Flechas  →  Moverse", True, WHITE)
    t3 = font_sm.render("Ratón           →  Apuntar", True, WHITE)
    t4 = font_sm.render("Clic izquierdo  →  Disparar", True, WHITE)
    t5 = font_sm.render("ESC             →  Salir", True, GREY)
    t6 = font_big.render("Pulsa ESPACIO para comenzar", True, YELLOW)
    cx = surface.get_width()//2
    surface.blit(t1, (cx - t1.get_width()//2, 100))
    for i, t in enumerate([t2,t3,t4,t5]):
        surface.blit(t, (cx - t.get_width()//2, 220 + i*40))
    surface.blit(t6, (cx - t6.get_width()//2, 430))

def screen_gameover(surface, player, wave, font_big, font_sm):
    surface.fill(BLACK)
    cx = surface.get_width()//2
    t1 = font_big.render("GAME OVER", True, RED)
    t2 = font_sm.render(f"Oleada alcanzada: {wave}", True, WHITE)
    t3 = font_big.render(f"Puntuación: {player.score}", True, ORANGE)
    t4 = font_sm.render("Pulsa ESPACIO para reiniciar  |  ESC para salir", True, GREY)
    surface.blit(t1, (cx - t1.get_width()//2, 140))
    surface.blit(t2, (cx - t2.get_width()//2, 230))
    surface.blit(t3, (cx - t3.get_width()//2, 290))
    surface.blit(t4, (cx - t4.get_width()//2, 420))

def screen_wave_clear(surface, wave, font_big, font_sm):
    cx, cy = surface.get_width()//2, surface.get_height()//2
    t1 = font_big.render(f"¡OLEADA {wave} COMPLETADA!", True, GREEN)
    t2 = font_sm.render("Prepárate para la siguiente...", True, WHITE)
    surface.blit(t1, (cx - t1.get_width()//2, cy - 40))
    surface.blit(t2, (cx - t2.get_width()//2, cy + 20))


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    pygame.init()
    pygame.display.set_caption("Arena 3D – Shooter")
    screen  = pygame.display.set_mode((W, H))
    buf     = pygame.Surface((W, H))  # buffer de renderizado
    clock   = pygame.time.Clock()

    font_big  = pygame.font.SysFont("monospace", 28, bold=True)
    font_sm   = pygame.font.SysFont("monospace", 20)
    font_tiny = pygame.font.SysFont("monospace", 15)

    # ── Estado ──
    STATE   = "intro"   # intro | playing | wave_clear | gameover
    player  = Player()
    wave    = 0
    enemies = []
    bullets = []
    particles = []
    kill_msgs = []       # lista de (texto, frames_restantes, color)
    wave_timer = 0
    last_shot  = 0
    SHOOT_CD   = 0.22    # segundos

    pygame.mouse.set_visible(False)
    pygame.event.set_grab(False)

    def start_game():
        nonlocal player, wave, enemies, bullets, particles, kill_msgs, wave_timer
        player     = Player()
        wave       = 1
        enemies    = spawn_wave(wave)
        bullets    = []
        particles  = []
        kill_msgs  = []
        wave_timer = 0

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        # ── Eventos ──
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_SPACE:
                    if STATE in ("intro", "gameover"):
                        start_game()
                        STATE = "playing"
                        pygame.mouse.set_visible(False)
                        pygame.event.set_grab(True)

            if event.type == pygame.MOUSEBUTTONDOWN and STATE == "playing":
                if event.button == 1:
                    now = time.time()
                    if now - last_shot >= SHOOT_CD:
                        last_shot = now
                        bullets.append(Bullet(player.x, player.y, player.angle))

        # ── Lógica de juego ──
        if STATE == "playing":
            # Mouse look
            mx, _ = pygame.mouse.get_rel()
            player.angle += mx * TURN_SPD * 60 * dt

            # Mover
            keys = pygame.key.get_pressed()
            player.move(keys, dt)

            # Balas
            for b in bullets[:]:
                b.update(dt)
                if not b.alive:
                    bullets.remove(b)
                    continue
                for e in enemies[:]:
                    if not e.alive: continue
                    if math.hypot(b.x - e.x, b.y - e.y) < e.size + 0.2:
                        e.hp -= 20
                        b.alive = False
                        # Partículas
                        for _ in range(6):
                            particles.append(Particle(e.x, e.y, e.color))
                        if e.hp <= 0:
                            e.alive = False
                            player.score += e.pts
                            msg = ("⚠ PESADO" if e.etype=='heavy'
                                   else "⚡ RÁPIDO" if e.etype=='fast'
                                   else "✓ Enemigo")
                            kill_msgs.insert(0, [msg + " eliminado", 120,
                                                 RED if e.etype=='heavy' else ORANGE if e.etype=='fast' else GREEN])
                        break

            # Enemigos
            for e in enemies:
                if not e.alive: continue
                dist = e.update(player, dt)
                if dist < 0.6:
                    player.take_damage(e.dmg * dt)
                    if player.hp <= 0:
                        STATE = "gameover"
                        pygame.event.set_grab(False)
                        pygame.mouse.set_visible(True)

            # Partículas
            for p in particles[:]:
                p.update()
                if not p.alive:
                    particles.remove(p)

            # Kill feed timer
            for km in kill_msgs[:]:
                km[1] -= 1
                if km[1] <= 0:
                    kill_msgs.remove(km)

            # ¿Oleada terminada?
            alive = [e for e in enemies if e.alive]
            if not alive and STATE == "playing":
                STATE = "wave_clear"
                wave_timer = 3.0

        elif STATE == "wave_clear":
            wave_timer -= dt
            if wave_timer <= 0:
                wave += 1
                enemies  = spawn_wave(wave)
                bullets  = []
                particles= []
                STATE = "playing"

        # ─────────────────────────────────────
        #  RENDERIZADO
        # ─────────────────────────────────────
        if STATE == "playing" or STATE == "wave_clear":
            # Cielo
            buf.fill(SKY)
            pygame.draw.rect(buf, FLOOR, (0, H//2, W, H//2))

            # Raycast
            depth_buf = cast_rays(buf, player)

            # Sprites enemigos
            draw_sprites(buf, player, enemies, depth_buf)

            # Particulas 2D en minimap (decorativo)
            # HUD
            draw_hud(buf, player, wave, kill_msgs, font_big, font_sm, font_tiny)
            draw_minimap(buf, player, enemies)

            if STATE == "wave_clear":
                overlay = pygame.Surface((W, H), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 90))
                buf.blit(overlay, (0, 0))
                screen_wave_clear(buf, wave, font_big, font_sm)

        elif STATE == "intro":
            screen_intro(buf, font_big, font_sm, font_tiny)

        elif STATE == "gameover":
            screen_gameover(buf, player, wave, font_big, font_sm)

        screen.blit(buf, (0, 0))

        # FPS
        fps_txt = font_tiny.render(f"{int(clock.get_fps())} FPS", True, GREY)
        screen.blit(fps_txt, (W - fps_txt.get_width() - 8, H - 20))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()