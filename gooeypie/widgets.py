import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
from tkinter import font
from functools import partial
from gooeypie.error import *
import platform

if platform.system() == 'Windows':
    OS = 'Windows'
if platform.system() == 'Darwin':
    OS = 'Mac'

try:
    from PIL import Image as PILImage, ImageTk
    PILLOW = True
except ImportError:
    PILImage = ImageTk = None
    PILLOW = False


class GooeyPieEvent:
    """Event objects are passed to callback functions"""
    def __init__(self, event_name, gooeypie_widget, tk_event=None):
        """Creates a GooeyPie event object, passed to all callback functions"""
        self.event_name = event_name
        self.widget = gooeypie_widget
        if tk_event:
            # All tk events report mouse position
            self.mouse = {
                'x': tk_event.x,
                'y': tk_event.y,
                'x_root': tk_event.x_root,
                'y_root': tk_event.y_root
            }

            # Mouse events set character information to the string '??'. Set to None in this case.
            if tk_event.char == '??':
                self.key = None
            else:
                self.key = {
                    'char': tk_event.char,
                    'keysym': tk_event.keysym,
                    'keycode': tk_event.keycode
                }
        else:
            self.mouse = None
            self.key = None


class GooeyPieWidget:
    """Base class for other GooeyPie widget classes, mostly for event handling"""

    # Event names in GooeyPie matched with their corresponding tk events
    _tk_event_mappings = {
        'mouse_down': '<Button-1>',
        'mouse_up': '<ButtonRelease-1>',
        'double_click': '<Double-Button-1>',
        'triple_click': '<Triple-Button-1>',
        'middle_click': '<Button-2>',
        'right_click': '<Button-3>',
        'mouse_over': '<Enter>',
        'mouse_out': '<Leave>',
        'key_press': '<Key>',
        'focus': '<FocusIn>',
        'blur': '<FocusOut>'
    }

    def __init__(self):
        # All events initially set to None
        self._events = {event_name: None for event_name in self._tk_event_mappings.keys()}
        self._disabled = False

    def _event(self, event_name, tk_event=None):
        """Constructs a GooeyPie Event object and calls the registered callback"""
        try:
            gooeypie_event = GooeyPieEvent(event_name, self, tk_event)
            self._events[event_name](gooeypie_event)
        except KeyError:
            raise AttributeError(f"'{event_name}' listener not associated with this widget")

    def _slider_change_event(self, event_name, slider_value):
        """In tkinter, slider change events send the new value of the slider, so this is a special callback"""

        # The slider's change event will be called whenever a movement is detected on the widget, even if the
        # movement does not actually change the value. The checks whether or not a change has actually been made.
        if self._value.get() != self._previous_value:
            self._previous_value = self._value.get()  # Update the previous value
            self._event(event_name)

    def _text_change_event(self, event_name, a, b, c):
        """To implement the change event for the Input/Textbox widget, a trace must be
        added to the variable associated with the Input. The trace command sends
        3 arguments to the callback"""
        self._event(event_name)

    def add_event_listener(self, event_name, callback):
        """Registers callback to respond to certain events"""

        # Check that the event is valid for the given widget
        if event_name not in self._events:
            raise GooeyPieError(f"The event '{event_name}' is not valid for widget {self}")

        # CHeck that the event function specified accepts a single argument
        if callback.__code__.co_argcount != 1:
            raise GooeyPieError(f'Your event function {callback.__name__}() must accept a single argument')

        self._events[event_name] = callback

        if event_name in self._tk_event_mappings:
            self.bind(self._tk_event_mappings[event_name], partial(self._event, event_name))

        if event_name == 'change':
            if isinstance(self, RadiogroupBase):
                # Add the event to each radiobutton in the group
                for radiobutton in self.winfo_children():
                    radiobutton.configure(command=partial(self._event, event_name))

            if isinstance(self, Slider):
                # The tk callback for a slider passes an argument that is the value of the slider
                self.configure(command=partial(self._slider_change_event, event_name))

            if isinstance(self, (Checkbox, Spinbox)):
                # change method available on Radiobutton and Checkbox objects
                self.configure(command=partial(self._event, event_name))

            if isinstance(self, Input):
                # Add a trace to the string variable associated with the Input for change
                # self._value.trace('w', lambda a, b, c: print('trace works...'))
                self._value.trace('w', partial(self._text_change_event, event_name))

            if isinstance(self, Textbox):
                # TODO: change event for the textbox is complicated - will need to add a 'sentinel' to the Textbox widget
                # http://webcache.googleusercontent.com/search?q=cache:KpbCmAzvn_cJ:code.activestate.com/recipes/464635-call-a-callback-when-a-tkintertext-is-modified/+&cd=2&hl=en&ct=clnk&gl=au
                self.bind('<<Modified>>', partial(self._event, event_name))

        if event_name == 'press':
            # press event only on buttons (for now perhaps...)
            self.configure(command=partial(self._event, event_name))

        if event_name == 'select':
            # Select event associated at the moment with listboxes and dropdowns
            if isinstance(self, Listbox):
                self.bind('<<ListboxSelect>>', partial(self._event, event_name))
            elif isinstance(self, Dropdown):
                self.bind('<<ComboboxSelected>>', partial(self._event, event_name))


    def remove_event_listener(self, event_name):
        """
        Removes an event listener from a widget
        No exceptions are raised if the event is not currently registered
        """
        try:
            self._events[event_name] = None
            if event_name in ('change', 'press'):
                self.configure(command='')
            else:
                self.unbind(self._tk_event_mappings[event_name])
        except KeyError:
            raise ValueError(f"Cannot remove event. '{event_name}' is not a valid event for {self}")

    # All widgets can be enabled and disabled
    @property
    def disabled(self):
        return self._disabled

    @disabled.setter
    def disabled(self, value):
        self._disabled = bool(value)
        if self._disabled:
            self.state(['disabled'])
        else:
            self.state(['!disabled'])


    # TODO: grid (layout) options? Can these be set prior to gridding, or only after they've been added?
    # Easy to implement by calling grid() on the widget - previously set options are not overridden unless specified
    # In fact, can call grid() at any time with options set - row/column will be set automatically though.

    # This allows for code like:
    #       button = gl.Button(app, 'Click me', callback)
    #       button.stretch/fill = True  <-- need words to describe fill_x and fill_y (haven't used x and y, so am wary...)
    #       button.align = 'right'    <-- could feasibly see this line being something that would be useful to a user
    #       button.valign = 'bottom'
    #       button.location = (2, 3)   <-- this feels counter to the general philosophy of gl.
    #           Why would a widget be moved to a different location after it has been added?
    #           Even still, maybe this should be a function, like button.move_to(2, 1)

    # Also users should be able to override the default padding set by add(). This should be possible either
    # before or after gridding. This means I definitely need a dictionary of these options)
    #       button.margin = 4               <-- all sides
    #       label.margin = (2, 4, 5, 1)     <-- top, right, bottom, left
    #       image.margin = (4, 6)           <-- top/bottom, left/right


    # TESTING: Retrieve all grid settings
    def get_info(self):
        return self.grid_info()
        # Sample output: Grid info: {'in': <guilite.GuiLiteApp object .!guiliteapp>, 'column': 1, 'row': 1, 'columnspan': 1, 'rowspan': 1, 'ipadx': 0, 'ipady': 0, 'padx': (0, 10), 'pady': (0, 10), 'sticky': 'nw'}


class Label(ttk.Label, GooeyPieWidget):
    def __init__(self, container, text):
        GooeyPieWidget.__init__(self)
        ttk.Label.__init__(self, container, text=text)

    @property
    def text(self):
        return self.cget('text')

    @text.setter
    def text(self, content):
        self.configure(text=content)

    def __str__(self):
        return f"<Label '{self.text}'>"

    # TODO: add the justify property
    # https://anzeljg.github.io/rin2/book2/2405/docs/tkinter/ttk-Label.html
    # Label.configure(justify='center|left|right')
    # Already did this for Input - copy across?


class Button(ttk.Button, GooeyPieWidget):
    def __init__(self, container, text, callback, min_size=10):
        GooeyPieWidget.__init__(self)
        ttk.Button.__init__(self, container, text=text)
        size = max(min_size, len(text) + 2)
        self.configure(width=size)
        self._events['press'] = None
        if callback:
            self.add_event_listener('press', callback)

    @property
    def width(self):
        return self.cget('width')

    @width.setter
    def width(self, value):
        self.configure(width=value)

    @property
    def text(self):
        return self.cget('text')

    @text.setter
    def text(self, text):
        self.configure(text=text)

    def __str__(self):
        return f"<Button '{self.text}'>"

    def __repr__(self):
        return self.__str__()

    # TESTING #
    def info(self):
        return self.grid_info()


class Slider(ttk.Scale, GooeyPieWidget):
    def __init__(self, container, low, high, orientation='horizontal'):
        GooeyPieWidget.__init__(self)
        self._events['change'] = None

        # The slider's value will be a float or int depending on the low/high parameter data type
        if isinstance(low, float) or isinstance(high, float):
            self._value = tk.DoubleVar()
        else:
            self._value = tk.IntVar()

        # The previous value is stored so that the change event is called only when the actual value changes
        self._previous_value = self._value.get()

        # Swap low and high for vertical orientation to change the weird default behaviour
        if orientation == 'vertical':
            low, high = high, low

        ttk.Scale.__init__(self, container, from_=low, to=high, orient=orientation, variable=self._value)

    def __str__(self):
        return f'<Slider from {self.cget("from")} to {self.cget("to")}>'

    @property
    def value(self):
        return self._value.get()

    @value.setter
    def value(self, val):
        self.set(val)

    @property
    def orientation(self):
        return self.cget('orient')

    @orientation.setter
    def orientation(self, direction):
        self.configure(orient=direction)


class StyleLabel(Label):
    """Formatted label"""

    def __init__(self, container, text):
        super().__init__(container, text)
        self._style = ttk.Style()
        self._style_id = f'{str(id(self))}.TLabel'  # Need a custom id for each instance
        self.configure(style=self._style_id)

    def _get_current_font(self):
        """Returns a dictionary representing the current font"""
        return font.Font(font=self._style.lookup(self._style_id, 'font')).actual()

    def _set_font(self, font_dict):
        font_string = [font_dict['family'], font_dict['size']]
        options = []
        if font_dict['weight'] == 'bold':
            options.append('bold')
        if font_dict['slant'] == 'italic':
            options.append('italic')
        if font_dict['underline'] == 1:
            options.append('underline')
        if font_dict['overstrike'] == 1:
            options.append('overstrike')

        font_string.append(' '.join(options))
        self._style.configure(self._style_id, font=font_string)

    def _set_font_property(self, key, value):
        new_font = self._get_current_font()
        new_font[key] = value
        self._set_font(new_font)

    def set_font(self, font, size, options=''):
        # flatten the args
        options = options.split(' ')
        self.font_name = font
        self.font_size = size
        for option in options:
            if option == 'bold':
                self.font_weight = 'bold'
            elif option == 'italic':
                self.font_style = 'italic'
            elif option == 'underline':
                self.underline = 'underline'
            elif option == 'strikethrough':
                self.strikethrough = 'strikethrough'
            else:
                raise ValueError(f"Font options must be a string of options that can include 'bold', 'italic', 'underline' or 'strikethrough'. You said {options}")

    def clear_styles(self):
        self._style.configure(self._style_id, font=font.nametofont('TkDefaultFont'))

    @property
    def font_name(self):
        return self._get_current_font()['family']

    @font_name.setter
    def font_name(self, value):
        if value == 'default':
            self._set_font_property('family', font.nametofont('TkDefaultFont').actual()['family'])
        else:
            self._set_font_property('family', value)

    @property
    def font_size(self):
        return self._get_current_font()['size']

    @font_size.setter
    def font_size(self, value):
        if value == 'default':
            self._set_font_property('size', font.nametofont('TkDefaultFont').actual()['size'])
        else:
            try:
                self._set_font_property('size', int(value))
            except ValueError:
                raise ValueError(f"Font size must be an integer or the string 'default' "
                                 f"(value specified was {value})")

    @property
    def font_weight(self):
        return self._get_current_font()['weight']

    @font_weight.setter
    def font_weight(self, value):
        try:
            ('bold', 'normal').index(value)
            self._set_font_property('weight', value)
        except ValueError:
            raise ValueError(f"Font weight must be either 'bold' or 'normal' (value specified was '{value}')")

    @property
    def font_style(self):
        if self._get_current_font()['slant'] == 'roman':
            return 'normal'
        else:
            return 'italic'

    @font_style.setter
    def font_style(self, value):
        try:
            ('italic', 'normal').index(value)
            self._set_font_property('slant', value)
        except ValueError:
            raise ValueError(f"Font style must be either 'italic' or 'normal' (value specified was '{value}')")

    @property
    def underline(self):
        current_font = self._style.lookup(self._style_id, 'font')
        if font.Font(font=current_font).actual()['underline'] == 0:
            return 'normal'
        else:
            return 'underline'

    @underline.setter
    def underline(self, value):
        try:
            # 0 for normal, 1 for underline
            self._set_font_property('underline', ('normal', 'underline').index(value))
        except ValueError:
            raise ValueError(f"Underline must be either 'underline' or 'normal' (value specified was '{value}')")

    @property
    def strikethrough(self):
        current_font = self._style.lookup(self._style_id, 'font')
        if font.Font(font=current_font).actual()['overstrike'] == 0:
            return 'normal'
        else:
            return 'strikethrough'

    @strikethrough.setter
    def strikethrough(self, value):
        try:
            # 0 for normal, 1 for strikethrough (overstrike in tk-land)
            self._set_font_property('overstrike', ('normal', 'strikethrough').index(value))
        except ValueError:
            raise ValueError(f"Strikethrough style must be either 'strikethrough' or 'normal' "
                             f"(value specified was '{value}')")

    @property
    def colour(self):
        current_colour = self._style.lookup(self._style_id, 'foreground')
        if current_colour == 'SystemWindowText':
            return 'default'
        else:
            return current_colour

    @colour.setter
    def colour(self, value):
        if value == 'default':
            self._style.configure(self._style_id, foreground='SystemWindowText')
        else:
            self._style.configure(self._style_id, foreground=value)

    @property
    def background_colour(self):
        current_colour = self._style.lookup(self._style_id, 'background')
        if current_colour == 'SystemButtonFace':
            return 'default'
        else:
            return current_colour

    @background_colour.setter
    def background_colour(self, value):
        if value == 'default':
            self._style.configure(self._style_id, background='SystemButtonFace')
        else:
            self._style.configure(self._style_id, background=value)

    # Function aliases for alternate spellings of colour
    color = colour
    background_color = background_colour

    # Helper function
    def elements_available(self):
        # Get widget elements
        style = self._style
        layout = str(style.layout('custom.TLabel'))
        print('Stylename = {}'.format('custom.TLabel'))
        print('Layout    = {}'.format(layout))
        elements=[]
        for n, x in enumerate(layout):
            if x=='(':
                element=""
                for y in layout[n+2:]:
                    if y != ',':
                        element=element+str(y)
                    else:
                        elements.append(element[:-1])
                        break
        print('\nElement(s) = {}\n'.format(elements))

        # Get options of widget elements
        for element in elements:
            print('{0:30} options: {1}'.format(
                element, style.element_options(element)))


class Hyperlink(StyleLabel, GooeyPieWidget):
    def __init__(self, container, text, url):
        GooeyPieWidget.__init__(self)
        StyleLabel.__init__(self, container, text)
        self.url = url
        self.colour = 'blue'
        self.underline = 'underline'
        self.bind('<Enter>', lambda e: self.configure(cursor='hand2'))
        self.bind('<Button-1>', self._open_link)

    def _open_link(self, e):
        import webbrowser
        webbrowser.open(self.url)


class Image(Label, GooeyPieWidget):
    def __init__(self, container, image):
        GooeyPieWidget.__init__(self)
        Label.__init__(self, container, None)
        self.image = image

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, image):
        image_extension = image[-3:]
        if not PILLOW and image_extension != 'gif':
            raise ValueError('Only gif images can be used at this time.')

        self._image = image

        if not PILLOW:
            self._tk_image = tk.PhotoImage(file=image)
        else:
            self._tk_image = ImageTk.PhotoImage(PILImage.open(image))

        self.configure(image=self._tk_image)

    def __str__(self):
        return f"""<Image '{self.image}'>"""

    # TODO: Overwrite the text setter to raise an error?


class Input(ttk.Entry, GooeyPieWidget):
    def __init__(self, container):
        GooeyPieWidget.__init__(self)
        self._value = tk.StringVar()
        ttk.Entry.__init__(self, container, textvariable=self._value)
        self.secret = False
        self._events['change'] = None

    # TODO: width property

    def __str__(self):
        return f"""<Entry object>"""

    @property
    def width(self):
        return self.cget('width')

    @width.setter
    def width(self, value):
        self.configure(width=value)

    @property
    def text(self):
        return self._value.get()

    @text.setter
    def text(self, value):
        self._value.set(value)

    @property
    def secret(self):
        return self.secret

    @secret.setter
    def secret(self, value):
        if value:
            self.configure(show='●')
        else:
            self.configure(show='')

    @property
    def justify(self):
        return self.cget('justify')

    @justify.setter
    def justify(self, value):
        self.configure(justify=value)

    # todo: select method that selects all text


class Secret(Input):
    def __init__(self, container):
        Input.__init__(self, container)
        self.configure(show='●')

    def unmask(self):
        self.configure(show='')

    def mask(self):
        self.configure(show='●')

    def toggle(self):
        if self.cget('show'):
            self.unmask()
        else:
            self.mask()


class Listbox(tk.Listbox, GooeyPieWidget):
    def __init__(self, container, items):
        GooeyPieWidget.__init__(self)
        tk.Listbox.__init__(self, container)

        # Configuration options to make the listbox look more like a ttk widget
        self.configure(borderwidth=1, relief='flat', font=font.nametofont('TkDefaultFont'), activestyle='none',
                       highlightcolor='systemHighlight', highlightthickness=1, exportselection=0)

        # Different border colour names for Windows and Mac
        # https://www.tcl.tk/man/tcl8.6/TkCmd/colors.htm
        if OS == 'Windows':
            self.configure(highlightbackground='systemGrayText')
        if OS == "Mac":
            self.configure(highlightbackground='systemBlackText')

        self.insert('end', *items)
        self._events['select'] = None

    def add_option(self, item):
        """Adds an item to the end of the listbox"""
        self.insert('end', item)

    def remove(self, index):
        """Removes the item at the given index"""
        # TODO: handle the case where index is None
        # TODO: naming is inconsistent with add_option!
        self.delete(index)

    @property
    def height(self):
        return self.cget('height')

    @height.setter
    def height(self, lines):
        self.configure(height=lines)

    @property
    def multiple_selection(self):
        return self.cget('selectmode') == 'extended'

    @multiple_selection.setter
    def multiple_selection(self, multiple):
        mode = 'extended' if multiple else 'browse'
        self.configure(selectmode=mode)

    @property
    def selected_index(self):
        """Returns the index, starting from 0, of the selected line. Returns None if nothing is selected and
        a list if multiple items are selected
        """
        select = self.curselection()
        if len(select) == 0:
            return None
        elif len(select) == 1:
            return select[0]
        else:
            return select

    @selected_index.setter
    def selected_index(self, index):
        """Selects the line at position 'index', counting from 0"""
        self.activate(index)
        self.selection_set(index)

    @property
    def selected(self):
        """Returns the item, items as a tuple, or None, selected in the listbox"""
        select = self.curselection()
        if len(select) == 0:
            return None
        elif len(select) == 1:
            return self.get(0, 'end')[select[0]]
        else:
            return [self.get(0, 'end')[index] for index in select]


class Textbox(scrolledtext.ScrolledText, GooeyPieWidget):
    def __init__(self, container, width=20, height=5):
        GooeyPieWidget.__init__(self)
        scrolledtext.ScrolledText.__init__(self, container, width=width, height=height)

        self.configure(borderwidth=1, relief='flat', font=font.nametofont('TkDefaultFont'),
                       wrap='word', highlightcolor='systemHighlight', highlightthickness=1)

        # Different border colour names for Windows and Mac
        # https://www.tcl.tk/man/tcl8.6/TkCmd/colors.htm
        if OS == 'Windows':
            self.configure(highlightbackground='systemGrayText')
        if OS == "Mac":
            self.configure(highlightbackground='systemBlackText')

        self.bind('<Tab>', self.focus_next_widget)
        self.bind('<Shift-Tab>', self.focus_previous_widget)
        self.bind('<Control-Tab>', self.insert_tab)
        # self._events['change'] = None

    # TODO: readonly option
    # https://stackoverflow.com/questions/3842155/is-there-a-way-to-make-the-tkinter-text-widget-read-only

    def __str__(self):
        return f"""<Textbox object>"""

    @staticmethod
    def focus_next_widget(event):
        """Overrides the default behaviour of inserting a tab character in a textbox instead of
        changing focus to the next widget
        """
        event.widget.tk_focusNext().focus()
        return 'break'

    @staticmethod
    def focus_previous_widget(event):
        """Overrides the default behaviour of inserting a tab character in a textbox instead of
        changing focus to the previous widget
        """
        event.widget.tk_focusPrev().focus()
        return 'break'

    @staticmethod
    def insert_tab(event):
        """Allows the user to insert a tab character into the textbox with ctrl"""
        event.widget.insert('current', '\t')
        return 'break'

    @property
    def width(self):
        return self.cget('width')

    @width.setter
    def width(self, cols):
        self.configure(width=cols)

    @property
    def height(self):
        return self.cget('width')

    @height.setter
    def height(self, rows):
        self.configure(height=rows)

    @property
    def text(self):
        """Get all text. Strip the trailing newline added by tkinter"""
        return self.get('1.0', 'end')[:-1]

    @text.setter
    def text(self, text):
        """Replaces the contents of the textbox"""
        self.clear()
        self.insert('1.0', text)

    def clear(self):
        """Clear the contents of the textbox"""
        self.delete('1.0', 'end')

    def append(self, text):
        self.text += text


class ImageButton(Button):
    def __init__(self, container, image, callback, text=''):
        super().__init__(container, text, callback, 0)
        image_extension = image[-3:]
        if not PILLOW and image_extension != 'gif':
            raise ValueError('Only gif images can be used at this time.')

        self._image = image

        if not PILLOW:
            self._tk_image = tk.PhotoImage(file=image)
        else:
            self._tk_image = ImageTk.PhotoImage(PILImage.open(image))

        self.configure(image=self._tk_image, compound='left' if text else 'image')

    @property
    def image_position(self):
        return self.cget('compound')

    @image_position.setter
    def image_position(self, position):
        """If an image button includes text, set where the image should appear relative to that text"""
        self.configure(compound=position)


class Checkbox(ttk.Checkbutton, GooeyPieWidget):
    def __init__(self, container, text):
        GooeyPieWidget.__init__(self)
        self._checked = tk.BooleanVar(value=False)
        ttk.Checkbutton.__init__(self, container, text=text, variable=self._checked)
        self.state(['!alternate'])
        self._events['change'] = None   # Checkboxes support the 'change' event

    def __str__(self):
        return f'''<Checkbox '{self.cget("text")}'>'''

    @property
    def checked(self):
        return self._checked.get()

    @checked.setter
    def checked(self, state):
        self._checked.set(state)


class RadiogroupBase(GooeyPieWidget):
    """Base class used by Radiogroup and LabelledRadiogroup"""
    def __init__(self, choices, orient):
        GooeyPieWidget.__init__(self)
        self._events['change'] = None   # Radiobuttons support the 'change' event
        self._selected = tk.StringVar()

        # If images are used (to be implemented, need to support passing a list of 2-tuples,
        # where first item is the image, second is the value returned

        if isinstance(choices, (list, tuple)):
            side = 'left' if orient == 'horizontal' else 'top'
            for choice in choices:
                radiobutton = ttk.Radiobutton(self, text=choice, variable=self._selected, value=choice)
                # TODO: don't hard code the padding (config file somewhere somehow)
                radiobutton.pack(expand=True, fill='x', padx=(2, 5), pady=2, side=side)

    @property
    def options(self):
        return tuple(widget.cget('text') for widget in self.winfo_children())

    @property
    def selected(self):
        if self._selected.get():
            return self._selected.get()
        else:
            return None

    @selected.setter
    def selected(self, value):
        self._selected.set(value)


class Radiogroup(ttk.Frame, RadiogroupBase):
    """A set of radio buttons"""
    def __init__(self, container, choices, orient='vertical'):
        ttk.Frame.__init__(self, container)
        RadiogroupBase.__init__(self, choices, orient)

    def __str__(self):
        return f'<Radiogroup {tuple(self.choices)}>'


class LabelRadiogroup(ttk.LabelFrame, RadiogroupBase):
    """A set of radio buttons in a label frame"""
    def __init__(self, container, title, choices, orient='vertical'):
        ttk.LabelFrame.__init__(self, container, text=title)
        RadiogroupBase.__init__(self, choices, orient)

    def __str__(self):
        return f'<LabelRadiogroup {tuple(self.options)}>'


class Dropdown(ttk.Combobox, GooeyPieWidget):
    def __init__(self, container, choices):
        GooeyPieWidget.__init__(self)
        ttk.Combobox.__init__(self, container, values=choices, exportselection=0)
        self.state(['readonly'])
        self._events['select'] = None
        self.choices = choices

    def __str__(self):
        return f'<Dropdown {tuple(self.choices)}>'

    @property
    def selected(self):
        index = self.current()
        if index == -1:
            return None
        else:
            return self.cget('values')[index]

    @selected.setter
    def selected(self, value):
        """Sets the given item """
        try:
            self.cget('values').index(value)
            self.set(value)
        except ValueError:
            raise ValueError(f"Cannot set Dropdown to '{value}' as it is not one of the options")

    @property
    def selected_index(self):
        index = self.current()
        if index == -1:
            return None
        else:
            return index

    @selected_index.setter
    def selected_index(self, index):
        try:
            self.current(index)
        except Exception:
            raise IndexError(f"Index {index} out of range")


class Spinbox(ttk.Spinbox, GooeyPieWidget):
    def __init__(self, container, low, high, increment=1):
        GooeyPieWidget.__init__(self)
        ttk.Spinbox.__init__(self, container, from_=low, to=high, increment=increment, wrap=True)
        self.set(low)
        self.width = len(str(high)) + 4
        self._events['change'] = None

    def __str__(self):
        return f'<Spinbox from {self.cget("from")} to {self.cget("to")}>'

    @property
    def value(self):
        return self.get()

    @value.setter
    def value(self, value):
        self.set(value)

    @property
    def width(self):
        return self.cget('width')

    @width.setter
    def width(self, value):
        """Sets the width of the spinbox in characters (includes the control buttons)"""
        self.configure(width=value)


class Table(ttk.Treeview, GooeyPieWidget):
    """For displaying tabular data"""
    def columns(self, cols):
        """Sets the column names of the table"""

    def add_data(self, data):
        """Adds a row of data to the table"""