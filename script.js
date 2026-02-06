// --- ভেরিয়েবল সেটআপ ---
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

const W = 900;
const H = 600;

// কালার কোড
const RED = '#C80000', GREEN = '#00C800', YELLOW = '#FFFF00';
const BLUE = '#0078FF', GOLD = '#FFD700', BLACK = '#000000', WHITE = '#FFFFFF';

// ইমেজ এবং সাউন্ড স্টোরেজ
const images = {};
const sounds = {};

function loadImage(key, src) {
    const img = new Image();
    img.src = src;
    images[key] = img;
}

function loadSound(key, src) {
    const aud = new Audio(src);
    aud.volume = 0.3;
    sounds[key] = aud;
}

function playSound(key) {
    if (sounds[key]) {
        sounds[key].currentTime = 0;
        sounds[key].play().catch(e => {});
    }
}

// এসেট লোড করা (আপনার assets ফোল্ডারে এই ফাইলগুলো থাকতে হবে)
try {
    loadImage('bg1', 'assets/bg1.png');
    loadImage('bg2', 'assets/bg2.png');
    loadImage('cover', 'assets/cover.png');
    for(let i=1; i<=6; i++) loadImage(`idle${i}`, `assets/idle${i}.png`);
    for(let i=1; i<=6; i++) loadImage(`run${i}`, `assets/running${i}.png`);
    for(let i=1; i<=6; i++) loadImage(`punch${i}`, `assets/punch${i}.png`);
    for(let i=1; i<=5; i++) loadImage(`lying${i}`, `assets/lying${i}.png`);
    for(let i=1; i<=6; i++) loadImage(`e_idle${i}`, `assets/enemy_idle${i}.png`);
    for(let i=1; i<=6; i++) loadImage(`e_punch${i}`, `assets/enemy_punch${i}.png`);
    for(let i=1; i<=8; i++) loadImage(`e_lying${i}`, `assets/enemy_lying${i}.png`);

    loadSound('intro', 'assets/introSound.mp3');
    loadSound('punch', 'assets/punchSound.mp3');
    loadSound('safe', 'assets/safeSound.mp3');
    loadSound('lying', 'assets/lyingSound.mp3');
} catch(e) { console.log("Asset loading error"); }

// গেম স্টেট এবং প্লেয়ার স্ট্যাটাস
const keys = { left: false, right: false };
let bx = 0, bx_cng = 5;
let player_x = 300, player_y = 300;
let player_max_health = 100, player_health = 100;
let player_damage = 25, player_defense = 0;
let current_score = 0, player_coins = 0;
let combo_count = 0, last_hit_time = 0, combo_timeout = 2000;
let power_meter = 0, using_ultimate = false;
let upgrade_costs = { damage: 30, health: 20, defense: 10 };
let enemy_x = 700, enemy_y = 300, enemies_killed = 0;
let is_boss_round = false, enemy_max_health = 100, enemy_health = 100, enemy_base_damage = 15;
let anim_k = { idle: 0, punch: 0, run: 0, lying: 0, e_idle: 0, e_punch: 0, e_lying: 0 };
let states = { idle: true, punch: false, run: false, safe: false, lying: false, dead: false };
let enemy_states = { idle: true, punch: false, lying: false, dead: false };
let enemy_cooldown = 1500, last_enemy_punch = 0;
let player_damage_taken = false, enemy_damage_taken = false, shake_intensity = 0;
let game_active = false, menu_active = true, shop_active = false;

// ড্রয়িং ফাংশনসমূহ
function drawRect(x, y, w, h, color) {
    ctx.fillStyle = color;
    ctx.fillRect(x, y, w, h);
}

function drawHealthBar(x, y, current, maximum, is_boss) {
    let ratio = Math.max(0, current / maximum);
    let w = is_boss ? 150 : 100, h = is_boss ? 15 : 10;
    drawRect(x - 2, y - 2, w + 4, h + 4, BLACK);
    drawRect(x, y, w, h, RED);
    let col = ratio > 0.5 ? GREEN : YELLOW;
    if (is_boss) col = '#B40000';
    drawRect(x, y, w * ratio, h, col);
}

function drawPowerBar(x, y, current) {
    let ratio = current / 100;
    let w = 100, h = 8;
    drawRect(x - 2, y - 2, w + 4, h + 4, BLACK);
    drawRect(x, y, w, h, '#323232');
    drawRect(x, y, w * ratio, h, BLUE);
}

function drawAnimation(prefix, k, x, y, count, scale = 1.0) {
    let index = Math.min(count, Math.floor((k / 120) * count) + 1);
    let img = images[prefix + index];
    if (img && img.complete) {
        ctx.drawImage(img, x, y, img.width * scale, img.height * scale);
    } else {
        drawRect(x, y, 50 * scale, 100 * scale, prefix.includes('e_') ? 'purple' : 'white');
    }
}

function drawBackground(x, y) {
    if (images['bg1'] && images['bg1'].complete) {
        ctx.drawImage(images['bg1'], x, y);
        ctx.drawImage(images['bg2'], x + 900, y);
        ctx.drawImage(images['bg1'], x + 1800, y);
    } else {
        drawRect(0, 0, W, H, '#333');
    }
}

// ইনপুট লজিক
function setKey(key, value) {
    keys[key] = value;
    if (game_active && !states.dead) {
        if (key === 'right') {
            states.run = value && (enemy_states.dead || enemy_x >= 360);
            states.idle = !states.run;
        }
        if (key === 'left') {
            if (value && !states.run) {
                states.safe = true; states.idle = false;
                playSound('safe');
            } else {
                states.safe = false; states.idle = true;
            }
        }
    }
}

function triggerPunch() {
    if (game_active && !states.dead && !states.run && !states.safe && !shop_active) {
        states.punch = true; states.idle = false;
        anim_k.punch = 0; using_ultimate = false;
        playSound('punch');
    } else if (menu_active) {
        menu_active = false; game_active = true;
        playSound('intro');
    } else if (states.dead) {
        location.reload();
    }
}

function triggerUltimate() {
    if (game_active && !states.dead && power_meter >= 100 && !shop_active) {
        states.punch = true; states.idle = false;
        anim_k.punch = 0; using_ultimate = true;
        power_meter = 0; playSound('punch');
    }
}

function toggleShop() {
    if (!game_active) return;
    shop_active = !shop_active;
    const shopUI = document.getElementById('shop-buttons');
    shopUI.style.display = shop_active ? 'block' : 'none';
    if (shop_active) updateShopUI();
}

function buyItem(type) {
    if (player_coins >= upgrade_costs[type]) {
        player_coins -= upgrade_costs[type];
        if (type === 'damage') { player_damage += 5; upgrade_costs.damage += 25; }
        else if (type === 'health') { player_max_health += 20; player_health = player_max_health; upgrade_costs.health += 25; }
        else if (type === 'defense') { player_defense += 2; upgrade_costs.defense += 25; }
        playSound('safe'); updateShopUI();
    }
}

function updateShopUI() {
    document.getElementById('shop-coins').innerText = `Coins: ${player_coins}`;
    const btns = document.getElementById('shop-buttons').getElementsByTagName('button');
    btns[0].innerText = `1. Damage +5 (Cost: ${upgrade_costs.damage})`;
    btns[1].innerText = `2. Max HP +20 (Cost: ${upgrade_costs.health})`;
    btns[2].innerText = `3. Defense +2 (Cost: ${upgrade_costs.defense})`;
}

// মেইন গেম লুপ
function gameLoop() {
    let current_time_ms = Date.now();
    ctx.clearRect(0, 0, W, H);

    let offset_x = 0, offset_y = 0;
    if (shake_intensity > 0) {
        offset_x = (Math.random() * shake_intensity * 2) - shake_intensity;
        offset_y = (Math.random() * shake_intensity * 2) - shake_intensity;
        shake_intensity--;
    }

    if (game_active) {
        drawBackground(bx + offset_x, 0 + offset_y);
    } else {
        if (images['cover'] && images['cover'].complete) ctx.drawImage(images['cover'], 0, 0);
        else drawRect(0,0,W,H, BLACK);
    }

    if (game_active && !shop_active) {
        if (combo_count > 0 && (current_time_ms - last_hit_time > combo_timeout)) combo_count = 0;

        let px = player_x + offset_x, py = player_y + offset_y;
        let ex = enemy_x + offset_x, ey = enemy_y + offset_y;

        // প্লেয়ার রেন্ডারিং
        if (states.dead) {
            states.lying = true;
            if (anim_k.lying < 110) anim_k.lying += 2;
            drawAnimation('lying', anim_k.lying, px - 50, py, 5);
        } 
        else if (states.punch) {
            anim_k.punch += using_ultimate ? 5 : 3;
            if (using_ultimate && anim_k.punch < 20) drawRect(0, 0, W, H, WHITE);
            drawAnimation('punch', anim_k.punch, px, py, 6);
            if (anim_k.punch >= 60 && anim_k.punch <= 80 && Math.abs((player_x + 60) - enemy_x) < 50 && !enemy_damage_taken && !enemy_states.dead) {
                enemy_health -= using_ultimate ? 60 : player_damage;
                shake_intensity = using_ultimate ? 20 : 5;
                combo_count++; last_hit_time = current_time_ms;
                if (!using_ultimate) power_meter = Math.min(100, power_meter + 10);
                enemy_damage_taken = true;
            }
            if (anim_k.punch >= 120) { anim_k.punch = 0; states.punch = false; states.idle = true; enemy_damage_taken = false; using_ultimate = false; }
        } 
        else if (states.safe) drawAnimation('lying', 0, px - 70, py, 5);
        else if (states.run) {
            if (enemy_states.dead || enemy_x >= 360) {
                bx -= bx_cng; enemy_x -= bx_cng;
                if (bx <= -1800) bx = 0;
                if (enemy_states.dead && enemy_x < -200) {
                    enemy_x = 900; enemy_states.dead = false; enemy_states.lying = false; enemy_states.idle = true;
                    anim_k.e_lying = 0; enemy_damage_taken = false; player_damage_taken = false;
                    enemies_killed++;
                    is_boss_round = enemies_killed % 5 === 0;
                    enemy_max_health = is_boss_round ? 300 : 100;
                    enemy_health = enemy_max_health;
                }
            }
            anim_k.run += 3; if (anim_k.run >= 120) anim_k.run = 0;
            drawAnimation('run', anim_k.run, px, py, 6);
        } 
        else { anim_k.idle += 1; if (anim_k.idle >= 120) anim_k.idle = 0; drawAnimation('idle', anim_k.idle, px, py, 6); }

        // এনিমি লজিক
        if (enemy_health <= 0 && !enemy_states.dead) {
            enemy_states.dead = true; enemy_states.lying = true;
            let reward = is_boss_round ? 50 : 10;
            current_score += (reward + (combo_count * 2)); player_coins += reward;
            playSound('lying');
        }

        if (enemy_states.lying) {
            if (anim_k.e_lying < 110) anim_k.e_lying += 2;
            drawAnimation('e_lying', anim_k.e_lying, ex + 20, ey, 8);
        }
        else if (enemy_states.punch) {
            anim_k.e_punch += 2;
            drawAnimation('e_punch', anim_k.e_punch, ex - 20, ey, 6, is_boss_round ? 1.2 : 1.0);
            if (anim_k.e_punch >= 60 && anim_k.e_punch <= 80 && Math.abs(enemy_x - (player_x + 60)) < 50 && !states.safe && !player_damage_taken && !states.dead) {
                let dmg = Math.max(5, (is_boss_round ? 30 : enemy_base_damage) - player_defense);
                player_health -= dmg; player_damage_taken = true; shake_intensity = 5; combo_count = 0;
                if (player_health <= 0) { states.dead = true; playSound('lying'); }
            }
            if (anim_k.e_punch >= 120) { anim_k.e_punch = 0; enemy_states.punch = false; enemy_states.idle = true; player_damage_taken = false; }
        }
        else {
            anim_k.e_idle += 1; if (anim_k.e_idle >= 120) anim_k.e_idle = 0;
            drawAnimation('e_idle', anim_k.e_idle, ex, ey, 6, is_boss_round ? 1.2 : 1.0);
            if (!states.dead && Math.abs(enemy_x - (player_x + 60)) < 50 && (current_time_ms - last_enemy_punch > enemy_cooldown)) {
                enemy_states.punch = true; enemy_states.idle = false; last_enemy_punch = current_time_ms; playSound('punch');
            }
        }

        // HUD (Health, Score, UI)
        drawHealthBar(player_x + 30, player_y - 50, player_health, player_max_health, false);
        drawPowerBar(player_x + 30, player_y - 35, power_meter);
        if (!enemy_states.dead) {
            drawHealthBar(enemy_x + 30, enemy_y - 20, enemy_health, enemy_max_health, is_boss_round);
            if (is_boss_round) { ctx.fillStyle = RED; ctx.font = '20px Arial'; ctx.fillText("BOSS", enemy_x + 55, enemy_y - 45); }
        }
        ctx.fillStyle = WHITE; ctx.font = '30px Arial'; ctx.fillText(`Score: ${current_score}`, 20, 40);
        ctx.fillStyle = GOLD; ctx.fillText(`Coins: ${player_coins}`, 20, 80);
        if (power_meter >= 100) { ctx.fillStyle = BLUE; ctx.font = '25px Arial'; ctx.fillText("ULTIMATE READY (Tap Ultimate)", player_x, player_y - 60); }
        if (combo_count > 1) { ctx.fillStyle = YELLOW; ctx.font = 'bold 40px Arial'; ctx.fillText(`${combo_count}x COMBO!`, W/2 - 100, 100); }
        if (states.dead) {
            ctx.fillStyle = RED; ctx.font = '80px Arial'; ctx.fillText("GAME OVER", W/2 - 210, H/3);
            ctx.fillStyle = WHITE; ctx.font = '20px Arial'; ctx.fillText("Tap Punch to Restart", W/2 - 100, H/2 + 240);
        }
    } 
    else if (menu_active) {
        ctx.fillStyle = WHITE; ctx.font = '30px Arial'; ctx.fillText("Tap 'Punch' to Start", W/2 - 140, H/2 + 20);
    }
    requestAnimationFrame(gameLoop);
}

requestAnimationFrame(gameLoop);