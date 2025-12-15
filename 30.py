import pygame
import random
import sys
import math
import time

# === DONANIM ABSTRAKSİYON KATMANI (HAL) ===
try:
    import numpy as np
except ImportError:
    import traceback
    traceback.print_exc()
    print("-" * 30)
    print("SİSTEM HATASI: 'numpy' modülü eksik.")
    print("Çözüm: Terminale 'pip install numpy' yazın.")
    input("Çıkmak için ENTER tuşuna basın...") 
    sys.exit()

# === SİSTEM SABİTLERİ ===
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
FPS = 60

# Renk Paleti
C_BG = (5, 5, 12)
C_GRID = (40, 0, 60)
C_GRID_LIGHT = (80, 0, 120)
C_TEXT_MAIN = (200, 240, 255)
C_ACCENT_CORRECT = (0, 255, 128)
C_ACCENT_WRONG = (255, 40, 60)
C_HINT = (255, 200, 0)

# === DSP SES MOTORU ===
class AudioEngine:
    def __init__(self):
        # Buffer 1024 yapılarak ses kırılmaları önlendi
        pygame.mixer.pre_init(44100, -16, 2, 1024)        
        pygame.mixer.init()
        self.sfx_cache = {}
        self._compile_audio_assets()
        
    def _oscillate(self, freq, duration, wave_type='sqr', slide=0):
        sample_rate = 44100
        n_samples = int(sample_rate * duration)
        t = np.linspace(0, duration, n_samples, endpoint=False)
        
        if slide != 0:
            freq = np.linspace(freq, freq + slide, n_samples)
        
        if wave_type == 'sin':
            wave = np.sin(2 * np.pi * freq * t)
        elif wave_type == 'sqr':
            wave = np.sign(np.sin(2 * np.pi * freq * t))
        elif wave_type == 'saw':
            wave = 2 * (t * freq - np.floor(t * freq + 0.5))
        elif wave_type == 'noise':
            wave = np.random.uniform(-1, 1, n_samples)
            
        envelope = np.exp(-3 * t / duration)
        wave = wave * envelope * 0.4 
        
        audio_data = (wave * 32767).astype(np.int16)
        stereo_signal = np.column_stack((audio_data, audio_data))
        return pygame.sndarray.make_sound(stereo_signal)

    def _compile_audio_assets(self):
        self.sfx_cache['hover'] = self._oscillate(600, 0.05, 'sqr', slide=-200)
        self.sfx_cache['correct'] = self._oscillate(880, 0.4, 'sin', slide=400)
        self.sfx_cache['wrong'] = self._oscillate(150, 0.5, 'saw', slide=-50)
        self.sfx_cache['type'] = self._oscillate(800, 0.03, 'noise')
        self.sfx_cache['boot'] = self._oscillate(440, 1.0, 'sin', slide=880)

    def trigger(self, name):
        if name in self.sfx_cache:
            self.sfx_cache[name].play()

# === VERİ KATMANI ===
LAYER_MAP = {
    1: "PHYSICAL", 2: "DATA LINK", 3: "NETWORK", 
    4: "TRANSPORT", 5: "SESSION", 6: "PRESENTATION", 7: "APPLICATION"
}

OSI_DATABASE = [
    # Katman 1 - Fiziksel
    {"q": "Bit akışı, Voltaj seviyeleri, Kablolama, Hub.", "layer": 1},
    {"q": "Fiber optik kablodaki ışık sinyalleri.", "layer": 1},
    {"q": "NIC (Ağ Kartı) ile Switch arasındaki elektrik sinyali.", "layer": 1},
    {"q": "Zayıflayan elektrik sinyallerini yeniden üreten Repeater (Tekrarlayıcı) burada çalışır.", "layer": 1},
    
    # Katman 2 - Veri Bağı
    {"q": "MAC Adresi (Fiziksel Adres) buradadır.", "layer": 2},
    {"q": "Switch ve Bridge cihazları burada çalışır.", "layer": 2},
    {"q": "Veri birimi 'Frame' (Çerçeve) olarak adlandırılır.", "layer": 2},
    {"q": "ARP Protokolü (IP'den MAC bulma) burada çalışır.", "layer": 2},
    {"q": "Çerçeveleme (Framing) yaparak Layer 1'den gelen bit dizisini anlamlı veri bloklarına dönüştürür.", "layer": 2},
    {"q": "CAM (Content Addressable Memory) tablosu MAC adreslerini portlara eşler.", "layer": 2}, 

    # Katman 3 - Ağ
    {"q": "Mantıksal adresleme (IP Adresi) yapılır.", "layer": 3},
    {"q": "Router (Yönlendirici) burada çalışır.", "layer": 3},
    {"q": "Veri birimi 'Packet' (Paket) ismini alır.", "layer": 3},
    {"q": "ICMP (Ping komutu) bu katmanda çalışır.", "layer": 3},
    {"q": "Adresleri yorumlamaktan ve verilerin izleyeceği yolu yönlendirmekten sorumludur.", "layer": 3},
    {"q": "Layer 3 Switch'ler, VLAN'lar arası yönlendirme yapabilir.", "layer": 3}, 

    # Katman 4 - Taşıma
    {"q": "Uçtan uca (End-to-End) iletişim sağlar.", "layer": 4},
    {"q": "TCP (Güvenli) ve UDP (Hızlı) protokolleri.", "layer": 4},
    {"q": "Veri 'Segment'lere bölünür.", "layer": 4},
    {"q": "Flow Control (Akış Kontrolü) ve Hata düzeltme.", "layer": 4},
    {"q": "Gönderen ve alıcı arasında öncelikle 'TCP 3-way handshake' ile bağlantı kurulur (Connection-Oriented).", "layer": 4},
    {"q": "Veriyi segmentlere böler ve her segmente port numarası ekler.", "layer": 4}, 

    # Katman 5 - Oturum
    {"q": "İki uygulama arasındaki diyaloğu yönetir.", "layer": 5},
    {"q": "Senkronizasyon noktaları (Checkpoint) ekler.", "layer": 5},
    {"q": "NetBIOS ve RPC protokolleri.", "layer": 5},
    {"q": "Ağ cihazları arasında oturum oluşturma, sürdürme ve sonlandırmayı yönetir.", "layer": 5}, 
    {"q": "Kimlik doğrulama ve yeniden bağlantıları kontrol ederek bilgi akışını yönetir.", "layer": 5}, 

    # Katman 6 - Sunum
    {"q": "Veri formatlama (JPEG, ASCII, MP3).", "layer": 6},
    {"q": "Encryption (Şifreleme) ve Decryption işlemleri.", "layer": 6},
    {"q": "Veri Sıkıştırma (Compression).", "layer": 6},
    {"q": "Kullanılabilecek çeşitli işletim sistemlerinde veri formatını göndericiden alıcıya çevirir.", "layer": 6}, 
    {"q": "SSL/TLS protokolünün şifreleme ve bütünlük kontrolü işlemleriyle ilişkilidir.", "layer": 6}, 

    # Katman 7 - Uygulamaj
    {"q": "Kullanıcıya en yakın katmandır.", "layer": 7},
    {"q": "HTTP, FTP, SMTP, DNS protokolleri.", "layer": 7},
    {"q": "Web tarayıcıları ve E-posta istemcileri.", "layer": 7},
    {"q": "Ağ servislerine erişmek için kullanıcılar ve uygulama işlemleri için bir pencere görevi görür.", "layer": 7}, 
    {"q": "Soket (IP adresi + port numarası) aracılığıyla süreçler arası iletişimi sağlar.", "layer": 7}, 
]

class GridSystem:
    def __init__(self):
        self.offset_y = 0
        self.speed = 2

    def render(self, surface):
        self.offset_y = (self.offset_y + self.speed) % 40
        cx = SCREEN_WIDTH // 2
        
        for i in range(-10, 11):
            x_start = cx + i * 80
            x_end = cx + i * 300
            pygame.draw.line(surface, C_GRID, (x_start, 0), (x_end, SCREEN_HEIGHT), 2)
            
        for i in range(SCREEN_HEIGHT // 40 + 2):
            y = i * 40 + self.offset_y
            color = C_GRID_LIGHT if y > 200 else C_GRID
            pygame.draw.line(surface, color, (0, y), (SCREEN_WIDTH, y), 2)

class Particle:
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        angle = random.uniform(0, 6.28)
        speed = random.uniform(3, 10)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.randint(30, 60)
        self.color = color
        self.size = random.randint(2, 6)
        self.gravity = 0.4

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.life -= 1
        self.size *= 0.95

    def render(self, surface):
        if self.life > 0:
            pygame.draw.rect(surface, self.color, (int(self.x), int(self.y), int(self.size), int(self.size)))

class IOPort:
    def __init__(self, layer_id, name, x, y, w, h):
        self.layer_id = layer_id
        self.name = name
        self.rect = pygame.Rect(x, y, w, h)
        self.base_y = y
        self.target_y = y
        self.highlight = None
        self.blink_timer = random.randint(0, 60)

    def update_logic(self, mx, my):
        is_hovered = self.rect.collidepoint(mx, my)
        self.target_y = self.base_y - 20 if is_hovered else self.base_y
        self.rect.y += (self.target_y - self.rect.y) * 0.2
        self.blink_timer += 1
        return is_hovered

    def render(self, surface, font_L, font_S):
        pygame.draw.line(surface, (50, 50, 70), (self.rect.centerx, self.rect.bottom), (self.rect.centerx, SCREEN_HEIGHT), 4)
        pygame.draw.rect(surface, (10, 10, 15), self.rect)
        
        if self.highlight:
            border_col = self.highlight
        elif self.rect.y < self.base_y - 5:
            border_col = (0, 255, 255)
        else:
            border_col = (60, 60, 80)
            
        pygame.draw.rect(surface, border_col, self.rect, 3)
        
        for i in range(3):
            is_on = (self.blink_timer // (10 + i * 5)) % 2 == 0
            led_col = border_col if is_on else (20, 20, 20)
            pygame.draw.circle(surface, led_col, (self.rect.x + 20 + i*15, self.rect.y + 15), 4)

        lbl = font_L.render(f"L{self.layer_id}", True, border_col)
        surface.blit(lbl, (self.rect.centerx - lbl.get_width()//2, self.rect.centery - 10))
        nm = font_S.render(self.name[:4], True, (150, 150, 150))
        surface.blit(nm, (self.rect.centerx - nm.get_width()//2, self.rect.bottom - 25))

# === ANA ÇEKİRDEK (KERNEL) ===
class CoreKernel:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("OSI DEFENDER v4.2 [STABLE]")
        self.clock = pygame.time.Clock()
        
        self.audio = AudioEngine()
        self.grid = GridSystem()
        self.particles = []
        self.ports = []
        
        # Font Yükleme (Hata korumalı)
        try:
            self.f_big = pygame.font.SysFont("consolas", 60, bold=True)
            self.f_mid = pygame.font.SysFont("consolas", 24, bold=True)
            self.f_small = pygame.font.SysFont("consolas", 14)
        except:
            self.f_big = pygame.font.Font(None, 60)
            self.f_mid = pygame.font.Font(None, 24)
            self.f_small = pygame.font.Font(None, 14)

        self._init_ports()
        
        # --- DEĞİŞKEN BAŞLATMA (MEMORY ALLOCATION) ---
        self.text_tick = 0   # HATA BURADAYDI: Bu satır eklendi
        self.char_idx = 0
        self.target_text = ""
        self.display_text = ""
        self.shake = 0
        self.score = 0
        self.integrity = 100
        # ---------------------------------------------
        
        self.state = 'MENU'
        self.audio.trigger('boot')

    def _init_ports(self):
        w, h, gap = 90, 130, 25
        total_w = 7 * w + 6 * gap
        start_x = (SCREEN_WIDTH - total_w) // 2
        for i in range(1, 8):
            self.ports.append(IOPort(i, LAYER_MAP[i], start_x + (i-1)*(w+gap), SCREEN_HEIGHT - 200, w, h))

    def soft_reset(self):
        self.score = 0
        self.integrity = 100
        self.particles.clear()
        self.q_pool = OSI_DATABASE.copy()
        random.shuffle(self.q_pool)
        self.next_question()
        self.state = 'RUN'
        self.audio.trigger('boot')

    def trigger_shake(self, magnitude):
        self.shake = magnitude

    def spawn_particles(self, x, y, color, count=30):
        for _ in range(count):
            self.particles.append(Particle(x, y, color))

    def next_question(self):
        for p in self.ports: p.highlight = None
        
        if not hasattr(self, 'q_pool') or not self.q_pool:
            self.q_pool = OSI_DATABASE.copy()
            random.shuffle(self.q_pool)
            
        self.current_q = self.q_pool.pop()
        self.target_text = self.current_q['q']
        self.display_text = ""
        self.char_idx = 0
        self.timer = 600

    def update_typewriter(self):
        if self.char_idx < len(self.target_text):
            self.text_tick += 1
            if self.text_tick % 2 == 0:
                self.display_text += self.target_text[self.char_idx]
                self.char_idx += 1
                self.audio.trigger('type')

    def run(self):
        running = True
        last_hover = None

        while running:
            mx, my = pygame.mouse.get_pos()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.soft_reset()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.state == 'MENU':
                        self.soft_reset()
                        
                    elif self.state == 'RUN':
                        for p in self.ports:
                            if p.rect.collidepoint(mx, my):
                                if p.layer_id == self.current_q['layer']:
                                    self.score += 100
                                    self.spawn_particles(mx, my, C_ACCENT_CORRECT, 40)
                                    self.audio.trigger('correct')
                                    self.next_question()
                                else:
                                    self.integrity -= 20
                                    self.spawn_particles(mx, my, C_ACCENT_WRONG, 40)
                                    self.trigger_shake(20)
                                    self.audio.trigger('wrong')
                                    p.highlight = C_ACCENT_WRONG
                                    for correct in self.ports:
                                        if correct.layer_id == self.current_q['layer']:
                                            correct.highlight = C_HINT
                                    self.state = 'FEEDBACK'
                                    self.wait_timer = 60

            ox, oy = 0, 0
            if self.shake > 0:
                ox = random.randint(-self.shake, self.shake)
                oy = random.randint(-self.shake, self.shake)
                self.shake = max(0, self.shake - 1)

            for p in self.particles: p.update()
            self.particles = [p for p in self.particles if p.life > 0]

            if self.state == 'RUN':
                self.update_typewriter()
                self.timer -= 1
                if self.timer <= 0:
                    self.integrity -= 10
                    self.trigger_shake(10)
                    self.next_question()
                if self.integrity <= 0: self.state = 'GAMEOVER'
                
                hovering_any = False
                for p in self.ports:
                    if p.update_logic(mx, my):
                        hovering_any = True
                        if last_hover != p:
                            self.audio.trigger('hover')
                            last_hover = p
                if not hovering_any: last_hover = None

            elif self.state == 'FEEDBACK':
                self.wait_timer -= 1
                if self.wait_timer <= 0:
                    self.next_question()
                    self.state = 'RUN'

            self.screen.fill(C_BG)
            bg_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            self.grid.render(bg_surf)
            self.screen.blit(bg_surf, (0, 0))

            if self.state == 'MENU':
                t1 = self.f_big.render("Eşleşme Oyunu", True, C_ACCENT_CORRECT)
                t2 = self.f_mid.render("Sistem Hazır // Başlatmak İçin Tıklayınız", True, C_TEXT_MAIN)
                self.screen.blit(t1, (SCREEN_WIDTH//2 - t1.get_width()//2 + ox, 300+oy))
                self.screen.blit(t2, (SCREEN_WIDTH//2 - t2.get_width()//2 + ox, 380+oy))

            elif self.state in ['RUN', 'FEEDBACK']:
                pygame.draw.rect(self.screen, (50,0,0), (20, 20, 300, 20))
                pygame.draw.rect(self.screen, C_ACCENT_CORRECT if self.integrity > 40 else C_ACCENT_WRONG, (20, 20, 3*self.integrity, 20))
                
                score_t = self.f_mid.render(f"Skor: {self.score}", True, C_TEXT_MAIN)
                self.screen.blit(score_t, (SCREEN_WIDTH - 250, 20))
                
                rst_hint = self.f_small.render("[R] Yeniden Başlat", True, (100, 100, 100))
                self.screen.blit(rst_hint, (SCREEN_WIDTH - 250, 50))

                q_rect = pygame.Rect(100+ox, 100+oy, SCREEN_WIDTH-200, 150)
                pygame.draw.rect(self.screen, (0, 0, 0, 200), q_rect)
                pygame.draw.rect(self.screen, C_GRID_LIGHT, q_rect, 2)
                
                words = self.display_text.split()
                lines = []
                curr_line = []
                for word in words:
                    if self.f_mid.size(' '.join(curr_line + [word]))[0] < q_rect.width - 40:
                        curr_line.append(word)
                    else:
                        lines.append(' '.join(curr_line))
                        curr_line = [word]
                lines.append(' '.join(curr_line))

                y_offset = q_rect.y + 30
                for line in lines:
                    txt_surf = self.f_mid.render(line, True, C_TEXT_MAIN)
                    self.screen.blit(txt_surf, (q_rect.centerx - txt_surf.get_width()//2, y_offset))
                    y_offset += 30
                
                if self.state == 'RUN':
                    time_width = (self.timer / 600) * (SCREEN_WIDTH-200)
                    pygame.draw.rect(self.screen, C_HINT, (100+ox, 260+oy, time_width, 5))

                for p in self.ports: p.render(self.screen, self.f_mid, self.f_small)

            elif self.state == 'GAMEOVER':
                t1 = self.f_big.render("Oyun Bitti", True, C_ACCENT_WRONG)
                t2 = self.f_mid.render(f"Final Skor: {self.score}", True, C_TEXT_MAIN)
                t3 = self.f_mid.render("Yeniden Başlatmak için [R] Tuşuna Tıklayınız", True, C_HINT)
                self.screen.blit(t1, (SCREEN_WIDTH//2 - t1.get_width()//2 + ox, 250+oy))
                self.screen.blit(t2, (SCREEN_WIDTH//2 - t2.get_width()//2 + ox, 330+oy))
                self.screen.blit(t3, (SCREEN_WIDTH//2 - t3.get_width()//2 + ox, 400+oy))

            for p in self.particles: p.render(self.screen)

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()

if __name__ == "__main__":
    CoreKernel().run()