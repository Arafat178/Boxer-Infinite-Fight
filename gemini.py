import pygame
from pygame import mixer
import random
import time

# --- Initialization ---
pygame.init()
pygame.mixer.init()
clock = pygame.time.Clock()

# --- Screen & Constants ---
W, H = 900, 600
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption('Boxer: Infinite Fight - RPG Upgrade Edition')

# --- Colors & Fonts ---
WHITE = (255, 255, 255)
RED = (200, 0, 0)
GREEN = (0, 200, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 120, 255)
GOLD = (255, 215, 0)
BLACK = (0, 0, 0)
GRAY_TRANSPARENT = (0, 0, 0, 180)

font_small = pygame.font.Font(pygame.font.get_default_font(), 20)
font_score = pygame.font.Font(pygame.font.get_default_font(), 30)
font_large = pygame.font.Font(pygame.font.get_default_font(), 50)
font_combo = pygame.font.SysFont("arial", 40, bold=True)

# --- Asset Loading ---
try:
    bg1 = pygame.image.load('assets/bg1.png').convert()
    bg2 = pygame.image.load('assets/bg2.png').convert()
except:
    # Fallback if bg missing
    bg1 = pygame.Surface((900, 600))
    bg1.fill((50, 50, 50))
    bg2 = bg1

try:
    cover_img = pygame.image.load('assets/cover.png').convert()
except:
    cover_img = pygame.Surface((W, H))
    cover_img.fill(BLACK)

# Sounds
def load_sound(path):
    try:
        s = mixer.Sound(path)
        s.set_volume(0.3)
        return s
    except:
        return None

intro_Sound = load_sound('assets/introSound.mp3')
punch_sound = load_sound('assets/punchSound.mp3')
enemy_punch_sound = load_sound('assets/punchSound.mp3') 
safeSound = load_sound('assets/safeSound.mp3')
lyingSound = load_sound('assets/lyingSound.mp3')
# New sounds (simulated with existing if specific ones don't exist)
coin_sound = load_sound('assets/safeSound.mp3') # Reuse safe sound for coin
ultimate_sound = load_sound('assets/punchSound.mp3') 

# --- Animation Loader ---
def load_anim(prefix, count):
    imgs = []
    for i in range(1, count + 1):
        try:
            img = pygame.image.load(f'assets/{prefix}{i}.png').convert_alpha()
            imgs.append(img)
        except:
            pass
    return imgs

idle_imgs = load_anim('idle', 6)
run_imgs = load_anim('running', 6)
punch_imgs = load_anim('punch', 6)
lying_imgs = load_anim('lying', 5)

enemy_idle_imgs = load_anim('enemy_idle', 6)
enemy_punch_imgs = load_anim('enemy_punch', 6)
enemy_lying_imgs = load_anim('enemy_lying', 8)

# --- Helper Functions ---
def draw_health_bar(surface, x, y, current, maximum, is_player=True, is_boss=False):
    ratio = current / maximum
    if ratio < 0: ratio = 0
    w = 150 if is_boss else 100
    h = 15 if is_boss else 10
    
    # Border
    pygame.draw.rect(surface, BLACK, (x - 2, y - 2, w + 4, h + 4))
    # Background
    pygame.draw.rect(surface, RED, (x, y, w, h))
    # Fill
    col = GREEN if ratio > 0.5 else YELLOW
    if is_boss: col = (180, 0, 0) # Dark red for boss
    pygame.draw.rect(surface, col, (x, y, w * ratio, h))

def draw_power_bar(surface, x, y, current):
    ratio = current / 100
    w, h = 100, 8
    pygame.draw.rect(surface, BLACK, (x - 2, y - 2, w + 4, h + 4))
    pygame.draw.rect(surface, (50, 50, 50), (x, y, w, h)) # Grey bg
    pygame.draw.rect(surface, BLUE, (x, y, w * ratio, h)) # Blue fill
    
    if current >= 100:
        # Glow effect hint
        pygame.draw.rect(surface, WHITE, (x, y, w, h), 1)

def background(x, y):
    screen.blit(bg1, (x, y))
    screen.blit(bg2, (x + 900, y))
    screen.blit(bg1, (x + 1800, y))

def draw_animation(imgs, x, y, k, scale=1.0):
    if not imgs: return
    total_frames = len(imgs)
    index = int((k / 120) * total_frames)
    if index >= total_frames: index = total_frames - 1
    
    img = imgs[index]
    if scale != 1.0:
        w = int(img.get_width() * scale)
        h = int(img.get_height() * scale)
        img = pygame.transform.scale(img, (w, h))
        
    screen.blit(img, (x, y))

# --- Game Variables ---

# Physics
bx = 0
by = 0 
bx_cng = 5 

# Player Stats (RPG System)
player_x = 300
player_y = 300
player_max_health = 100
player_health = 100
player_damage = 25
player_defense = 0 # Reduces incoming damage
current_score = 0
player_coins = 0

# Combo System
combo_count = 0
last_hit_time = 0
combo_timeout = 2000 # 2 seconds to reset combo

# Power System
power_meter = 0
is_ultimate_ready = False
using_ultimate = False

# Shop & Upgrades
shop_active = False
upgrade_costs = {
    'damage': 50,
    'health': 50,
    'defense': 50
}

# Enemy Stats & Boss System
enemy_x = 700
enemy_y = 300
enemies_killed = 0
is_boss_round = False

enemy_max_health = 100
enemy_health = 100
enemy_base_damage = 15

# Animation Counters
anim_k = {
    'idle': 0, 'punch': 0, 'run': 0, 'lying': 0,
    'e_idle': 0, 'e_punch': 0, 'e_lying': 0
}

# State Flags
states = {
    'idle': True, 'punch': False, 'run': False,
    'safe': False, 'lying': False, 'dead': False
}

enemy_states = {'idle': True, 'punch': False, 'lying': False, 'dead': False}
enemy_cooldown = 1500 
last_enemy_punch = 0

# Damage Flags (Prevent double hits)
player_damage_taken = False 
enemy_damage_taken = False 

# Visual Effects
shake_intensity = 0

# Game Flow
game_active = False
menu_active = True

# --- Main Loop ---
running = True
while running:
    
    current_time_ms = pygame.time.get_ticks()

    # 1. Screen Shake
    display_offset = (0, 0)
    if shake_intensity > 0:
        display_offset = (random.randint(-shake_intensity, shake_intensity), random.randint(-shake_intensity, shake_intensity))
        shake_intensity -= 1
    
    # 2. Draw Background
    if game_active:
        background(bx + display_offset[0], by + display_offset[1])
    else:
        screen.blit(cover_img, (0, 0))

    # 3. Event Handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if shop_active:
                    shop_active = False # Close shop
                else:
                    running = False
            
            # --- Menu Controls ---
            if menu_active:
                if event.key == pygame.K_s:
                    game_active = True
                    menu_active = False
                    if intro_Sound: intro_Sound.play() 
            
            # --- Shop Controls ---
            elif shop_active:
                if event.key == pygame.K_b: # Close shop
                    shop_active = False
                
                # Buy Damage
                if event.key == pygame.K_1:
                    if player_coins >= upgrade_costs['damage']:
                        player_coins -= upgrade_costs['damage']
                        player_damage += 5
                        upgrade_costs['damage'] += 25
                        if coin_sound: coin_sound.play()

                # Buy Health
                if event.key == pygame.K_2:
                    if player_coins >= upgrade_costs['health']:
                        player_coins -= upgrade_costs['health']
                        player_max_health += 20
                        player_health = player_max_health # Heal on upgrade
                        upgrade_costs['health'] += 25
                        if coin_sound: coin_sound.play()

                # Buy Defense
                if event.key == pygame.K_3:
                    if player_coins >= upgrade_costs['defense']:
                        player_coins -= upgrade_costs['defense']
                        player_defense += 2
                        upgrade_costs['defense'] += 25
                        if coin_sound: coin_sound.play()

            # --- Game Controls ---
            elif game_active and not states['dead']:
                
                # Open Shop
                if event.key == pygame.K_b and not states['punch'] and not enemy_states['punch']:
                    shop_active = True

                # Movement
                if event.key == pygame.K_RIGHT and not states['punch'] and not states['safe']:
                    if enemy_states['dead'] or enemy_x >= 360:
                        states['run'] = True
                        states['idle'] = False
                
                # Block
                if event.key == pygame.K_LEFT and not states['run']:
                    states['safe'] = True
                    states['idle'] = False
                    if safeSound: safeSound.play() 

                # Punch
                if event.key == pygame.K_SPACE and not states['run'] and not states['safe']:
                    states['punch'] = True
                    states['idle'] = False
                    anim_k['punch'] = 0
                    using_ultimate = False # Normal punch
                    if punch_sound: punch_sound.play() 

                # ULTIMATE PUNCH
                if event.key == pygame.K_f and not states['run'] and not states['safe']:
                    if power_meter >= 100:
                        states['punch'] = True
                        states['idle'] = False
                        anim_k['punch'] = 0
                        using_ultimate = True # Flag for huge damage
                        power_meter = 0 # Reset power
                        if ultimate_sound: ultimate_sound.play()

        if event.type == pygame.KEYUP:
            if game_active and not states['dead']:
                if event.key == pygame.K_RIGHT:
                    states['run'] = False
                    states['idle'] = True
                if event.key == pygame.K_LEFT:
                    states['safe'] = False
                    states['idle'] = True

    # 4. Game Logic (Only update if shop is closed)
    if game_active and not shop_active:
        
        # COMBO DECAY LOGIC
        if combo_count > 0 and (current_time_ms - last_hit_time > combo_timeout):
            combo_count = 0 # Reset combo if too slow

        # Draw positions
        px = player_x + display_offset[0]
        py = player_y + display_offset[1]
        ex = enemy_x + display_offset[0]
        ey = enemy_y + display_offset[1]
        
        # --- PLAYER LOGIC ---
        if states['dead']:
            states['lying'] = True
            states['idle'] = False
            states['punch'] = False
            
            if anim_k['lying'] < 110: anim_k['lying'] += 2
            draw_animation(lying_imgs, px - 50, py, anim_k['lying'])

        elif states['punch']:
            # Animation speed: Normal = 3, Ultimate = 5 (Faster)
            speed = 5 if using_ultimate else 3
            anim_k['punch'] += speed
            
            # Visual flare for Ultimate
            if using_ultimate and anim_k['punch'] < 20:
                screen.fill(WHITE) # Flash screen
            
            draw_animation(punch_imgs, px, py, anim_k['punch'])
            
            # HIT LOGIC
            # Hit window: Frames 60-80
            if 60 <= anim_k['punch'] <= 80:
                if abs(player_x + 60 - enemy_x) < 50 and not enemy_damage_taken and not enemy_states['dead']:
                    
                    # Calculate Damage
                    damage = 60 if using_ultimate else player_damage
                    enemy_health -= damage
                    
                    # Screen Shake
                    shake_intensity = 20 if using_ultimate else 5
                    
                    # Combo & Power Logic
                    combo_count += 1
                    last_hit_time = current_time_ms
                    if not using_ultimate:
                        power_meter += 10 # Gain power on normal hits
                        if power_meter > 100: power_meter = 100
                    
                    enemy_damage_taken = True
                    
            if anim_k['punch'] >= 120:
                anim_k['punch'] = 0
                states['punch'] = False
                states['idle'] = True
                enemy_damage_taken = False
                using_ultimate = False

        elif states['safe']:
            screen.blit(lying_imgs[0], (px - 70, py))

        elif states['run']:
            # Move world
            if enemy_states['dead'] or enemy_x >= 360:
                bx -= bx_cng
                enemy_x -= bx_cng
                if bx <= -1800: bx = 0
                
                # SPAWN NEW ENEMY
                if enemy_states['dead'] and enemy_x < -200:
                    enemy_x = 900
                    enemy_states['dead'] = False
                    enemy_states['lying'] = False
                    enemy_states['idle'] = True
                    anim_k['e_lying'] = 0
                    enemy_damage_taken = False
                    player_damage_taken = False
                    
                    # BOSS SPAWN LOGIC
                    enemies_killed += 1
                    if enemies_killed > 0 and enemies_killed % 5 == 0:
                        is_boss_round = True
                        enemy_max_health = 300
                        enemy_health = 300
                        # Boss doesn't do more damage, but is tanky
                    else:
                        is_boss_round = False
                        enemy_max_health = 100
                        enemy_health = 100

            anim_k['run'] += 3
            if anim_k['run'] >= 120: anim_k['run'] = 0
            draw_animation(run_imgs, px, py, anim_k['run'])

        else: # Idle
            anim_k['idle'] += 1
            if anim_k['idle'] >= 120: anim_k['idle'] = 0
            draw_animation(idle_imgs, px, py, anim_k['idle'])

        # --- ENEMY LOGIC ---
        
        # Death
        if enemy_health <= 0 and not enemy_states['dead']:
            enemy_states['dead'] = True
            enemy_states['lying'] = True
            
            # Rewards
            reward = 50 if is_boss_round else 10
            bonus = combo_count * 2 # Combo Bonus
            current_score += (reward + bonus)
            player_coins += reward
            
            if lyingSound: lyingSound.play()

        if enemy_states['lying']:
            if anim_k['e_lying'] < 110: anim_k['e_lying'] += 2
            draw_animation(enemy_lying_imgs, ex + 20, ey, anim_k['e_lying'])

        elif enemy_states['punch']:
            anim_k['e_punch'] += 2
            
            # Boss Scale
            scale = 1.2 if is_boss_round else 1.0
            draw_animation(enemy_punch_imgs, ex - 20, ey, anim_k['e_punch'], scale)
            
            # Player Hit
            if 60 <= anim_k['e_punch'] <= 80:
                if abs(enemy_x - (player_x + 60)) < 50 and not states['safe'] and not player_damage_taken:
                     if not states['dead']: 
                         
                         # Calculate incoming damage
                         dmg = 30 if is_boss_round else enemy_base_damage
                         dmg -= player_defense # Apply defense upgrade
                         if dmg < 5: dmg = 5 # Minimum damage
                         
                         player_health -= dmg
                         player_damage_taken = True
                         shake_intensity = 5
                         
                         # Reset combo on hit
                         combo_count = 0
                         
                         if player_health <= 0:
                             states['dead'] = True
                             if lyingSound: lyingSound.play()

            if anim_k['e_punch'] >= 120:
                anim_k['e_punch'] = 0
                enemy_states['punch'] = False
                enemy_states['idle'] = True
                player_damage_taken = False 

        else: # Enemy Idle
            anim_k['e_idle'] += 1
            if anim_k['e_idle'] >= 120: anim_k['e_idle'] = 0
            
            scale = 1.2 if is_boss_round else 1.0
            draw_animation(enemy_idle_imgs, ex, ey, anim_k['e_idle'], scale)

            # AI
            if not states['dead']: 
                if abs(enemy_x - (player_x + 60)) < 50 and (current_time_ms - last_enemy_punch > enemy_cooldown):
                    enemy_states['punch'] = True
                    enemy_states['idle'] = False
                    last_enemy_punch = current_time_ms
                    if enemy_punch_sound: enemy_punch_sound.play()

    # --- UI & OVERLAYS ---
    if game_active:
        # Player UI
        draw_health_bar(screen, player_x + 30, player_y - 30, player_health, player_max_health, True)
        draw_power_bar(screen, player_x + 30, player_y - 15, power_meter)
        
        # Enemy UI
        if not enemy_states['dead']:
            draw_health_bar(screen, enemy_x + 30, enemy_y - 20, enemy_health, enemy_max_health, False, is_boss_round)
            if is_boss_round:
                boss_txt = font_small.render("BOSS", True, RED)
                screen.blit(boss_txt, (enemy_x + 55, enemy_y - 45))

        # HUD
        score_text = font_score.render(f"Score: {current_score}", True, WHITE)
        coin_text = font_score.render(f"Coins: {player_coins}", True, GOLD)
        screen.blit(score_text, (20, 20))
        screen.blit(coin_text, (20, 60))
        
        shop_hint = font_small.render("[B] Shop", True, WHITE)
        screen.blit(shop_hint, (20, 100))

        # Ultimate Ready Text
        if power_meter >= 100:
            ult_text = font_small.render("PRESS [F] FOR ULTIMATE!", True, BLUE)
            screen.blit(ult_text, (player_x, player_y - 50))

        # Combo Text
        if combo_count > 1:
            combo_surf = font_combo.render(f"{combo_count}x COMBO!", True, YELLOW)
            screen.blit(combo_surf, (W//2 - 100, 100))

        # Shop Overlay
        if shop_active:
            # Darken bg
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill(GRAY_TRANSPARENT)
            screen.blit(overlay, (0,0))
            
            # Shop Menu
            title = font_large.render("UPGRADE SHOP", True, GOLD)
            coins_ui = font_score.render(f"Your Coins: {player_coins}", True, WHITE)
            
            item1 = font_score.render(f"[1] Damage +5  (Cost: {upgrade_costs['damage']})", True, WHITE)
            item2 = font_score.render(f"[2] Max HP +20 (Cost: {upgrade_costs['health']})", True, WHITE)
            item3 = font_score.render(f"[3] Defense +2 (Cost: {upgrade_costs['defense']})", True, WHITE)
            exit_ui = font_small.render("Press [B] to Resume", True, YELLOW)
            
            cx, cy = W//2 - 150, 150
            screen.blit(title, (cx, cy))
            screen.blit(coins_ui, (cx, cy + 60))
            screen.blit(item1, (cx, cy + 120))
            screen.blit(item2, (cx, cy + 170))
            screen.blit(item3, (cx, cy + 220))
            screen.blit(exit_ui, (cx, cy + 300))

        if states['dead']:
            over_text = font_large.render("GAME OVER", True, RED)
            restart_text = font_score.render("Press ESC to Quit", True, WHITE)
            screen.blit(over_text, (W//2 - 120, H//2))
            screen.blit(restart_text, (W//2 - 110, H//2 + 60))
            
    else: # Main Menu
        title_text = font_large.render("BOXER LEGEND RPG", True, YELLOW)
        start_text = font_score.render("Press 'S' to Start", True, WHITE)
        screen.blit(title_text, (W//2 - 200, H//2 - 50))
        screen.blit(start_text, (W//2 - 100, H//2 + 20))

    pygame.display.update()
    clock.tick(60)

pygame.quit()