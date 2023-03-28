import modules.scripts as scripts
import gradio as gr
import os

from modules import images
from modules.processing import process_images, Processed
from modules.processing import Processed
from modules.shared import opts, cmd_opts, state

from PIL import Image, ImageDraw

class Script(scripts.Script):

# The title of the script. This is what will be displayed in the dropdown menu.
    def title(self):

        return "Corridor Crawler Outpainting"


# Determines when the script should be shown in the dropdown menu via the
# returned value. As an example:
# is_img2img is True if the current tab is img2img, and False if it is txt2img.
# Thus, return is_img2img to only show the script on the img2img tab.

    def show(self, is_img2img):

        return is_img2img #TODO: Require sub-tab to be "Inpaint upload"

# How the script's is displayed in the UI. See https://gradio.app/docs/#components
# for the different UI components you can use and how to create them.
# Most UI components can return a value, such as a boolean for a checkbox.
# The returned values are passed to the run method as parameters.

    def ui(self, is_img2img):

        myPath = str(scripts.basedir())
        prefab_img = Image.open(str(myPath + "/extensions/corridor-crawler-outpainting/prefabs/art-museum.png")) #Change art-museum.png to desired prefab image

        prefab = gr.Image(value=prefab_img, shape=[512, 512], type="pil", label="Prefab Image") #The prefab dungeon image which will be placed around all step images

        csteps = gr.Slider(minimum=1.0, maximum=30.0, step=1.0, value=1.0,
        label="Number of Corridor Steps") #How many times the script should loop using the newest generated corridor image

        with gr.Accordion(label="Animation", open=False):
            gr.Markdown("Currently only works if you leave Advanced Settings at the default values.")

            animation_enabled = gr.Checkbox(label="Animation enabled?")
            #animation_direction = gr.Dropdown(label="Animation Direction", choices=["Zoom In", "Zoom Out"], value="Zoom In")
            animation_frames = gr.Slider(minimum=0.0, maximum=120, step=1.0, value=20, label="Animated Frames Per Step (0 for a slideshow-style gif of all steps)")
            animation_duration = gr.Slider(minimum=1.0, maximum=1000, step=1.0, value=50, label="Milliseconds per Frame")
            animation_size = gr.Slider(minimum=1.0, maximum=1024.0, step=1.0, value=256.0,label="Animation Size (X and Y)")
            animation_save_path = gr.Textbox(label="Save Animation To (WARNING: May overwrite if same filename used)", value=str(myPath + "/outputs/animation.gif"))



        with gr.Accordion(label="Advanced Settings", open=False):
            gr.Markdown("Change the size and position of where each step image will be pasted onto the prefab image. Only change this if you are using a different mask image!")

            thumbnail_size_x = gr.Slider(minimum=1.0, maximum=768.0, step=1.0, value=256.0,label="Thumbnail Size X")
            thumbnail_size_y = gr.Slider(minimum=1.0, maximum=768.0, step=1.0, value=256.0,label="Thumbnail Size Y")

            thumbnail_pos_x = gr.Slider(minimum=1.0, maximum=768.0, step=1.0, value=127.0,label="Thumbnail Position X")
            thumbnail_pos_y = gr.Slider(minimum=1.0, maximum=768.0, step=1.0, value=81.0,label="Thumbnail Position Y")

        return [prefab, csteps, thumbnail_size_x, thumbnail_size_y, thumbnail_pos_x, thumbnail_pos_y, animation_enabled, animation_frames, animation_duration, animation_size, animation_save_path]



# This is where the additional processing is implemented. The parameters include
# self, the model object "p" (a StableDiffusionProcessing class, see
# processing.py), and the parameters returned by the ui method.
# Custom functions can be defined here, and additional libraries can be imported
# to be used in processing. The return value should be a Processed object, which is
# what is returned by the process_images method.

    def run(self, p, prefab, csteps, thumbnail_size_x, thumbnail_size_y, thumbnail_pos_x, thumbnail_pos_y, animation_enabled, animation_frames, animation_duration, animation_size, animation_save_path):

        step_images = [] #List to contain each generated step, will be used for animations

        def newStep(prev_step):
            #Return a single new step image, pasting prev_step into a copy of the prefab image

            im = prefab.copy() #Start with a copy of the prefab image
            step = prev_step #Modify the size/pos of the previous step
            step.thumbnail((thumbnail_size_x, thumbnail_size_y))
            im.paste(step, (thumbnail_pos_x, thumbnail_pos_y)) #Paste resized step into prefab image

            return im

        def animation(frame_num, time_per_frame, save_indiv=False):
            #Returns a list of frames for the animation

            # Determine the coordinates to paste Image2 onto Image1
            # THIS ONLY WORKS WITH THE DEFAULT 'ADVANCED SETTINGS'!
            image2_coords = (254, 162)

            def combine_steps(im1, im2):
                # Generate and return a single 1024x1024 picture containing two steps, im1 will be doubled in scale and im2 will be pasted on top at regular size

                # First, create im3 as a copy of im1
                im3 = im1.copy()

                # Double the size of Image1 to 1024x1024
                # THIS ONLY WORKS ASSUMING THE PREFAB IS DOUBLE THE SIZE OF THE STEP IMAGE, WHICH IS THE DEFAULT IN 'ADVANCED SETTINGS'
                im3 = im3.resize((1024, 1024))

                # Paste Image2 onto Image1
                im3.paste(im2, image2_coords)

                # Return the new image
                return im3 #img3.save('NewImage.jpg')

            def animate_step(input_img):
                # Determine the size of Image2 in the input_img
                image2_size = (512, 512)
                
                # Determine the step size for the rectangular image_mask
                step_size = [int(image2_coords[i]/(frame_num-1)) for i in range(2)]
                size_step = [int((1024-image2_size[i])/(frame_num-1)) for i in range(2)]
                
                # Create a list to store the frames
                frame_list = []
                
                # Generate each frame
                for i in range(frame_num):
                    # Create the rectangular image_mask
                    mask_size = [1024 - size_step[j]*i for j in range(2)]
                    mask_coords = [step_size[j]*i for j in range(2)]
                    mask_box = tuple(mask_coords + [mask_coords[j] + mask_size[j] for j in range(2)])
                    mask = Image.new('L', input_img.size, 0)
                    mask_draw = ImageDraw.Draw(mask)
                    mask_draw.rectangle(mask_box, fill=255)
                    
                    # Crop the desired part of input_img using the image_mask
                    crop_img = Image.composite(input_img, Image.new('RGB', input_img.size, (255, 255, 255)), mask)
                    crop_img = crop_img.crop(mask_box)
                    
                    # Scale down the frame to animation_size
                    crop_img.thumbnail((animation_size, animation_size))
                    
                    # Add the new image to the list of frames
                    frame_list.append(crop_img)
                
                # Return the list of frames
                return frame_list

            # Hold all lists of frames in a bigger list
            big_frame_list = []

            for i in range(len(step_images)-1):
                # Combine the steps and then animate for every step in the list
                im1 = step_images[i]
                im2 = step_images[i+1]
                im3 = combine_steps(im1, im2)
                
                # Animate the new animation frames for im3
                new_frames = animate_step(im3)

                # Add new frames to bigger frame list
                big_frame_list.extend(new_frames)

                # TODO: Add options for saving individual gifs
                '''
                # Save individual gifs for each step, if option enabled
                if(save_indiv):
                    new_frames[0].save(str(i)+'step-animation.gif', save_all=True, optimize=True, append_images=new_frames[1:], duration=time_per_frame, loop=0)
                '''
            
            #Return the big final gif frames
            return big_frame_list #big_frame_list[0].save("big-animation.gif", save_all=True, optimize=True, append_images=big_frame_list[1:], duration=time_per_frame, loop=0)


        """ TODO: Label generated images with each step number
        basename = ""
        if csteps != 0:
            basename += "steps_" + str(csteps) #Save step number in image title
        """


        proc = None #Placeholder variable for processed images
        myPrevStep = p.init_images[0] #The initial step image uploaded by user, NOT the prefab image

        i = 0
        while i < csteps: #Repeat once for each cstep

            p.init_images[0] = newStep(myPrevStep)
            proc = process_images(p) #THIS IS WHERE THE ACTUAL STABLE DIFFUSION PROCESSING HAPPENS

            myPrevStep = proc.images[0] #Set myPrevStep to processed image result, which will then be used in the next loop

            step_images.insert(0, myPrevStep.copy()) #Add to step_images, for animations and other post-processing effects

            i += 1

        if(animation_enabled): #Save animation gif if animation enabled
            my_animation = animation(animation_frames, animation_duration)
            my_animation[0].save(animation_save_path, save_all=True, append_images=my_animation[1:], optimize=True, duration=animation_duration, loop=0)

        return proc
