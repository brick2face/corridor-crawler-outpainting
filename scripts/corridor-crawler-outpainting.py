import modules.scripts as scripts
import gradio as gr
import os

from modules import images
from modules.processing import process_images, Processed
from modules.processing import Processed
from modules.shared import opts, cmd_opts, state

from PIL import Image

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
            gr.Markdown("Currently the only animation type available is slideshow-style gifs. Help would be deeply appreciated on the corridor-crawler-outpainting GitHub to add more advanced types of animations, and more filetypes (webm, mp4, etc.).")
            """
            animation_type = gr.Dropdown(label="Animation Type", choices=["None (no animation)", "Simple Slideshow"], value="None (no animation)")
            animation_direction = gr.Dropdown(label="Animation Direction", choices=["Zoom In", "Zoom Out"], value="Zoom In")
            """
            animation_enabled = gr.Checkbox(label="Animation enabled?")
            animation_duration = gr.Slider(minimum=1.0, maximum=10000, step=1.0, value=500, label="Time per Frame (milliseconds)")
            animation_save_path = gr.Textbox(label="Save Animation To (WARNING: May overwrite if same filename used)", value=str(myPath + "/outputs/animation.gif"))



        with gr.Accordion(label="Advanced Settings", open=False):
            gr.Markdown("Change the size and position of where each step image will be pasted onto the prefab image. Only change this if you are using a different mask image!")

            thumbnail_size_x = gr.Slider(minimum=1.0, maximum=768.0, step=1.0, value=256.0,label="Thumbnail Size X")
            thumbnail_size_y = gr.Slider(minimum=1.0, maximum=768.0, step=1.0, value=256.0,label="Thumbnail Size Y")

            thumbnail_pos_x = gr.Slider(minimum=1.0, maximum=768.0, step=1.0, value=127.0,label="Thumbnail Position X")
            thumbnail_pos_y = gr.Slider(minimum=1.0, maximum=768.0, step=1.0, value=81.0,label="Thumbnail Position Y")

        return [prefab, csteps, thumbnail_size_x, thumbnail_size_y, thumbnail_pos_x, thumbnail_pos_y, animation_enabled, animation_duration, animation_save_path]



# This is where the additional processing is implemented. The parameters include
# self, the model object "p" (a StableDiffusionProcessing class, see
# processing.py), and the parameters returned by the ui method.
# Custom functions can be defined here, and additional libraries can be imported
# to be used in processing. The return value should be a Processed object, which is
# what is returned by the process_images method.

    def run(self, p, prefab, csteps, thumbnail_size_x, thumbnail_size_y, thumbnail_pos_x, thumbnail_pos_y, animation_enabled, animation_duration,animation_save_path):

        step_images = [] #List to contain each generated step, will be used for animations

        def newStep(prev_step):
            #Return a single new step image, pasting prev_step into a copy of the prefab image

            im = prefab.copy() #Start with a copy of the prefab image
            step = prev_step #Modify the size/pos of the previous step
            step.thumbnail((thumbnail_size_x, thumbnail_size_y))
            im.paste(step, (thumbnail_pos_x, thumbnail_pos_y)) #Paste resized step into prefab image

            return im


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

            step_images.append(myPrevStep.copy()) #Add to step_images, for animations and other post-processing effects

            i += 1

        if(animation_enabled): #Save animation gif if animation enabled
            step_images[0].save(animation_save_path, save_all=True, append_images=step_images[1:], optimize=True, duration=animation_duration, loop=0)

        return proc
