import sys

import pygame as pg
from pygame import Rect
from pygame.locals import *

# Screen Dimensions
WIDTH = 1000
HEIGHT = 500

# Loading Images
troll_img_1 = pg.image.load('Troll1.png')
troll_small_img_1 = pg.transform.scale(troll_img_1, (64, 64))       #Shrinks the picture from 320x320 pixels to 64x64 pixels
troll_img_2 = pg.image.load('Troll2.png')
troll_small_img_2 = pg.transform.scale(troll_img_2, (64, 64))
crate_img = pg.image.load('level_1\\2.png')
background_img = pg.image.load('Level_.png')
full_size_background = pg.transform.scale(background_img, (1000, 500)) #Grows the background picture from 100x50 pixels to 1000x500 pixels

# Starting up PyGame
pg.init()


class Hitbox(Rect):
    def __init__(self, left, top, width, height):
        super().__init__(left, top, width, height)      # Pass coordinates to the parent (Rect) class
        self.vx = 0                                     # Set x and y velocities to 0 (These are not currently used, they are for future plans)
        self.vy = 0
        self.img_1 = troll_small_img_1                  # Give 2 images as attributes and set the first one to be the one currently being used
        self.img_2 = troll_small_img_2
        self.current_img = self.img_1
    
    def draw(self, surface):
        surface.blit(self.current_img, self)            # Draw the current img at the location of the hitbox (the 'self' argument works as a location because we have Rect abilities)
    
    def erase(self, surface):                           # Not currently used, so left blank
        pass

    def move(self, dx, dy, obstacles=None):             # Move dx in the x direction and dy in the y direction, but move less than that if you hit something on the way
        if obstacles is None:
            obstacles = []
        # Movement in the x direction----------
        dest_rect = Rect(self).move(dx, 0)
        for obstacle in obstacles:
            if dest_rect.colliderect(obstacle):
                if dx > 0:
                    dest_rect.right = obstacle.left
                else:
                    dest_rect.left = obstacle.right
        # -------------------------------------
        # Movement in the y direction----------
        dest_rect.move_ip(0, dy)
        for obstacle in obstacles:
            if dest_rect.colliderect(obstacle):
                if dy > 0:
                    dest_rect.bottom = obstacle.top
                    self.vy = 0
                    self.grounded_timer = 2             # Grounded timer is also for future plans not currently used
                else:
                    dest_rect.top = obstacle.bottom
                    self.vy = 0
        # -------------------------------------
        self.update(dest_rect)

    def change_img(self):                           # Switch between the two pictures
        if self.current_img == self.img_1:
            self.current_img = self.img_2
        else:
            self.current_img = self.img_1


class Block(Rect):
    def __init__(self, left, top, width, height, img):      # Create a block using dimensions and an image
        super().__init__(left, top, width, height)
        self.img = img                      

    def draw(self, surface):
        surface.blit(self.img, self)


screen = pg.display.set_mode((WIDTH, HEIGHT))               # Create the screen object


hb = Hitbox(500, 250, 64, 64)                               # Create our hitbox, roughly in the middle of the screen


# Making Crates------------------------------------------------------------
crates = []
crate_left_edge_1 = 200
crate_left_edge_2 = 800
crate_top_edge_1 = 50
crate_top_edge_2 = 450

for top_edge in range(0, 500, 16):                                            #Make the left vertical line of crates
    crates.append(Block(crate_left_edge_1, top_edge, 16, 16, crate_img))

for top_edge in range(0, 500, 16):                                            #Make the right vertical line of crates
    crates.append(Block(crate_left_edge_2, top_edge, 16, 16, crate_img))

for left_edge in range(0, 1000, 16):                                          #Make the top horizontal line of crates
    crates.append(Block(left_edge, crate_top_edge_1, 16, 16, crate_img))

for left_edge in range(0, 1000, 16):                                          #Make the bottom horizontal line of crates
    crates.append(Block(left_edge, crate_top_edge_2, 16, 16, crate_img))
#--------------------------------------------------------------------------

clock = pg.time.Clock()             # Create a clock to control framerate


# The Game Loop -----------------------------------------------------------
while True:
    for event in pg.event.get():       # If the X is pressed, close pygame and then python itself
        if event.type == pg.QUIT:
            pg.quit()
            sys.exit()

    dx = 0                              # Start each frame assuming the hitbox is not going to move
    dy = 0

    keys_pressed = pg.key.get_pressed()

    if keys_pressed[K_RIGHT]:           # Set the intended movement based on the arrow keys that are pressed
        dx = 5
    elif keys_pressed[K_LEFT]:
        dx = -5

    if keys_pressed[K_UP]:
        dy = -5
    elif keys_pressed[K_DOWN]:
        dy = 5

    if keys_pressed[K_SPACE]:           # If spacebar is pressed, swap which image is the current image
        hb.change_img()

    screen.blit(full_size_background, (0, 0))   # Redraw the background so that our troll doesn't smear out behind

    for crate in crates:                        # Redraw the crates so they aren't hidden under the freshly drawn background
        crate.draw(screen)

    hb.move(dx, dy, obstacles=crates)           # Move our hitbox, but using the crates as the obstacles that restrict movement
    hb.draw(screen)                             # Draw the hitbox at its new position

    pg.display.flip()                           # Make all of the changes actually appear on screen

    clock.tick(30)                              # Wait if necessary, so that the framerate doesn't go above 30 frames per second
