from pathlib import Path
import sys

import numpy as np
from PIL import Image
import pygame as pg
from pygame import Rect
from pygame.locals import *

LEVEL_FILE = 'level2.txt'
WIDTH = 1280
HEIGHT = 640
BG_COLOUR = 'white'
GRAVITY = 1
JUMP_VELOCITY = 10
COLOUR_KEY = 'white'

COLOUR_TO_TYPE = {
    (255, 255, 255): '0',
    (0, 0, 0): '1',
    (255, 0, 0): '2',
    (0, 255, 0): '3',
    (0, 0, 255): '4',
    (255, 255, 0): '5',
    (255, 0, 255): '6',
    (0, 255, 255): '7',
}

REUSABLE_IMGS = {
    'fireball': pg.image.load('fireball.png')
}


def layout_from_png(png_path):
    png_path = Path(png_path)
    img = Image.open(png_path).convert('RGB')
    img_array = np.array(img)
    dest_file = png_path.with_suffix('.txt')
    with open(dest_file, 'w') as f:
        for row in img_array:
            for pixel in row:
                colour = tuple(pixel)
                f.write(COLOUR_TO_TYPE[colour])
            f.write('\n')


class Hitbox(Rect):
    def __init__(self, left, top, width, height):
        super().__init__(left, top, width, height)
        self.spawnpoint = (left, top)
        self.vx = 0
        self.vy = 0
        self.grounded_timer = 0

    def move(self, dx, dy, obstacles=None):
        if obstacles is None:
            obstacles = []

        self.grounded_timer = max(0, self.grounded_timer - 1)

        dest_rect = Rect(self).move(dx, 0)
        for obstacle in obstacles:
            if dest_rect.colliderect(obstacle):
                if dx > 0:
                    dest_rect.right = obstacle.left
                else:
                    dest_rect.left = obstacle.right
        dest_rect.move_ip(0, dy)
        for obstacle in obstacles:
            if dest_rect.colliderect(obstacle):
                if dy > 0:
                    dest_rect.bottom = obstacle.top
                    self.vy = 0
                    self.grounded_timer = 2
                else:
                    dest_rect.top = obstacle.bottom
                    self.vy = 0
        self.update(dest_rect)

    def draw(self, surface):
        pg.draw.rect(surface, 'red', self, width=1)
    
    def erase(self, surface):
        pg.draw.rect(surface, BG_COLOUR, self, width=1)

    def set_vx(self, vx):
        self.vx = vx

    def gravity(self):
        self.vy += GRAVITY

    def jump(self):
        if self.grounded_timer:
            self.vy -= JUMP_VELOCITY

    def update_position(self, obstacles):
        self.move(self.vx, self.vy, obstacles)

    def respawn(self):
        self.topleft = self.spawnpoint
        self.vx = 0
        self.vy = 0
        self.grounded_timer = 0



class Sprite:
    def __init__(self, left, top, width, height):
        self.hb = Hitbox(left, top, width, height)
        self.facing = 'R'
        self.state = 'idle'
        self.animations = {}
        self.fireball_cooldown = 0

    @classmethod
    def from_folder(cls, x, y, folder_path):
        animations = []
        for animation_folder in Path(folder_path).iterdir():
            animations.append((animation_folder.stem, 
                              Animation_Frames.from_folder(animation_folder)))
        width, height = animations[0][1].current_frame.get_size()
        sprite = cls(x, y, width, height)
        for state, animation in animations:
            sprite.register_animation(state, animation)
        return sprite

    @classmethod
    def from_image(cls, x, y, img):
        animation = Animation_Frames([img], [1])
        width, height = img.get_size()
        sprite = cls(x, y, width, height)
        sprite.register_animation('idle', animation)
        return sprite

    def draw(self, surface):
        current_frame = self.animations[self.state].current_frame
        if not self.facing == 'R':
            current_frame = pg.transform.flip(current_frame, True, False)
        surface.blit(current_frame, self.hb)

    def erase(self, surface):
        pg.draw.rect(surface, BG_COLOUR, self.hb)

    def register_animation(self, state, animation):
        self.animations[state] = animation

    def throw_fireball(self):
        if not self.fireball_cooldown:
            self.fireball_cooldown = 5
            return Fireball(self.hb.right, self.hb.centery, self.facing)

    def update_state(self):
        previous_state = self.state

        if not self.hb.grounded_timer:
            self.state = 'jump'
        elif self.hb.vx == 0:
            self.state = 'idle'
        else:
            self.state = 'run'
        
        if self.hb.vx > 0:
            self.facing = 'R'
        elif self.hb.vx < 0:
            self.facing = 'L'

        if self.state != previous_state:
            self.animations[self.state].reset()
        else:
            self.animations[self.state].advance()

        self.fireball_cooldown = max(0, self.fireball_cooldown - 1)


class Animation_Frames:
    def __init__(self, frames, durations=None):
        self.frames = frames
        self.durations = durations
        self.current_frame_idx = 0
        self.duration_elapsed = 0
        self.update_current_frame()
    
    @classmethod
    def from_folder(cls, folder_path):
        frames = []
        for img_file in Path(folder_path).iterdir(): 
            img = pg.image.load(img_file)
            img.set_colorkey(COLOUR_KEY)
            frames.append(img)
        return cls(frames)

    def update_current_frame(self):
        self.current_frame = self.frames[self.current_frame_idx]

    def advance(self):
        self.duration_elapsed += 1
        if self.duration_elapsed >= self.durations[self.current_frame_idx]:
            self.current_frame_idx = (self.current_frame_idx + 1) % len(self.frames)
            self.duration_elapsed = 0
        self.update_current_frame()

    def reset(self):
        self.current_frame_idx = 0
        self.update_current_frame()

    def set_shared_duration(self, duration):
        self.durations = [duration] * len(self.frames)


class Block(Rect):
    def __init__(self, left, top, width, height, img):
        super().__init__(left, top, width, height)
        self.img = img

    @classmethod
    def from_imgfile(cls, left, top, imgfile_path, scale=0):
        img = pg.image.load(imgfile_path)
        width, height = img.get_size()
        if scale:
            img = pg.transform.scale(img, (int(scale*width), int(scale*height)))
            width, height = img.get_size()
        return cls(left, top, width, height, img)

    def draw(self, surface):
        surface.blit(self.img, self)

    def erase(self, surface):
        pg.draw.rect(surface, BG_COLOUR, self)


class Fireball(Sprite):
    speed = 10
    img = REUSABLE_IMGS['fireball']
    img.set_colorkey(COLOUR_KEY)
    width, height = img.get_size()
    animation = Animation_Frames([img], [1])

    def __init__(self, left, top, facing='R'):
        super().__init__(left, top, self.width, self.height)
        self.register_animation('idle', self.animation)
        self.facing = facing
        self.duration = 10

    def update(self, surface, obstacles):
        self.erase(surface)


        if self.facing == 'R':
            self.hb.move(self.speed, 0, obstacles)
        elif self.facing == 'L':
            self.hb.move(-self.speed, 0, obstacles)

        self.draw(surface)

        self.duration -= 1

        if not self.duration:
            self.erase(surface)




class Walker(Sprite):
    speed = 1
    img = pg.image.load('guy\\walk\\guy.png')
    img.set_colorkey(COLOUR_KEY)
    width, height = img.get_size()
    animation = Animation_Frames.from_folder('guy\\walk')
    animation.set_shared_duration(1)

    def __init__(self, left, top, facing='R'):

        super().__init__(left, top, self.width, self.height)
        self.facing = facing
        self.register_animation('walk', self.animation)
        self.state = 'walk'

    def turn_around(self):
        if self.facing == 'R':
            self.facing = 'L'
        elif self.facing == 'L':
            self.facing = 'R'

    def die(self, surface):
        self.erase(surface)
        scream_sound.play()

    def update(self, surface, obstacles):
        self.erase(surface)

        if self.facing == 'R':
            self.hb.move_ip(self.speed, 0)
        elif self.facing == 'L':
            self.hb.move_ip(-self.speed, 0)

        self.draw(surface)
        for block in obstacles:
            if self.hb.colliderect(block):
                self.turn_around()
                break

        if Rect(self.hb).move(0, 5).collidelist(obstacles) == -1:
            self.turn_around()



def blocks_from_folder(folder_path):
    folder_path = Path(folder_path)
    layout_file = folder_path / LEVEL_FILE
    with open(layout_file) as f:
        block_layout = [list(row.strip()) for row in f]
    block_height = (HEIGHT//2)/len(block_layout)
    block_width = (WIDTH//2)/len(block_layout[0])
    walkers = []
    blocks = []
    stars = []
    for row_idx, row in enumerate(block_layout):
        for block_idx, block_type in enumerate(row):
            if block_type != '0':
                left = block_idx*block_width
                top = row_idx*block_height
                img_file = folder_path / f'{block_type}.png'
                if block_type == '6':
                    walkers.append(Walker(left, top))
                elif block_type == '7':
                    stars.append(Block.from_imgfile(left, top, img_file))
                else:
                    blocks.append(Block.from_imgfile(left, top, img_file))
    return stars, blocks, walkers

pg.init()

jump_sound = pg.mixer.Sound('jump.wav')
fireball_sound = pg.mixer.Sound('fireball.wav')
scream_sound = pg.mixer.Sound('scream.wav')

FONT = pg.font.SysFont('elephant', 20)
START_TEXT = FONT.render('Get to the Star', False, 'black')
WIN_TEXT = FONT.render('You Win!', False, 'black')

clock = pg.time.Clock()

screen = pg.display.set_mode((WIDTH, HEIGHT))

scaled = pg.Surface((WIDTH//2, HEIGHT//2))

scaled.fill(BG_COLOUR)

stars, blocks, walkers = blocks_from_folder('level_1')

scaled.blit(START_TEXT, (WIDTH//4 - START_TEXT.get_size()[0]//2, 100, *START_TEXT.get_size()))

screen.blit(pg.transform.scale(scaled, (WIDTH, HEIGHT)), (0, 0))

pg.display.flip()

pg.time.wait(2000)

pg.draw.rect(scaled, BG_COLOUR, (WIDTH//4 - START_TEXT.get_size()[0]//2, 100, *START_TEXT.get_size()))


for block in blocks:
    block.draw(scaled)

for star in stars:
    star.draw(scaled)

hero = Sprite.from_folder(20, 290, 'hero')
for animation_frames in hero.animations.values():
    animation_frames.set_shared_duration(10)


fireballs = []

dx = 0


while True:

    for star in stars:
        if hero.hb.colliderect(star):
            scaled.blit(WIN_TEXT, (WIDTH//4 - START_TEXT.get_size()[0]//2, 100, *WIN_TEXT.get_size()))
            screen.blit(pg.transform.scale(scaled, (WIDTH, HEIGHT)), (0, 0))
            pg.display.flip()
            pg.time.wait(2000)
            pg.quit()
            sys.exit()

    for walker in walkers:
        walker.update(scaled, blocks)

    for fireball in fireballs:
        fireball.update(scaled, blocks)

    hero.erase(scaled)

    hero.hb.update_position(blocks)

    hero.update_state()

    hero.draw(scaled)

    for walker in walkers:
        for fireball in fireballs:
            if fireball.hb.colliderect(walker.hb):
                walker.die(scaled)
                walkers.remove(walker)

    for walker in walkers:
        if hero.hb.colliderect(walker.hb):
            hero.erase(scaled)
            hero.hb.respawn()

    up_scaled = pg.transform.scale(scaled, (WIDTH, HEIGHT))

    screen.blit(up_scaled, (0, 0))

    pg.display.flip()

    for event in pg.event.get():
        if event.type == pg.QUIT:
            pg.quit()
            sys.exit()
    
    dx = 0

    keys_pressed = pg.key.get_pressed()
    if keys_pressed[K_RIGHT]:
        dx = 5
    elif keys_pressed[K_LEFT]:
        dx = -5

    if keys_pressed[K_UP]:
        hero.hb.jump()
        jump_sound.play()
    
    if keys_pressed[K_DOWN]:
        if fireball := hero.throw_fireball():
            fireballs.append(fireball)
            fireball_sound.play()

    hero.hb.set_vx(dx)

    hero.hb.gravity()

    fireballs = [fireball for fireball in fireballs if fireball.duration]
        
    clock.tick(30)
