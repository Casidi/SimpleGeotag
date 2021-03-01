#Requirements: wxPython, pyslip, Pillow, piexif

import os
import glob
import wx
import pyslip

from PIL import Image
import piexif
from fractions import Fraction

from appstaticbox import AppStaticBox
from rotextctrl import ROTextCtrl

HorizSpacer = 5
VertSpacer = 5

def to_deg(value, loc):
    """convert decimal coordinates into degrees, munutes and seconds tuple
    Keyword arguments: value is float gps-value, loc is direction list ["S", "N"] or ["W", "E"]
    return: tuple like (25, 13, 48.343 ,'N')
    """
    if value < 0:
        loc_value = loc[0]
    elif value > 0:
        loc_value = loc[1]
    else:
        loc_value = ""
    abs_value = abs(value)
    deg =  int(abs_value)
    t1 = (abs_value-deg)*60
    min = int(t1)
    sec = round((t1 - min)* 60, 5)
    return (deg, min, sec, loc_value)

def change_to_rational(number):
    """convert a number to rantional
    Keyword arguments: number
    return: tuple like (1, 2), (numerator, denominator)
    """
    f = Fraction(str(number))
    return (f.numerator, f.denominator)

class AppFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title='JC Geotag Tool')

        self.panel = wx.Panel(self, wx.ID_ANY)
        self.panel.SetBackgroundColour(wx.WHITE)
        self.panel.ClearBackground()
        all_display = wx.BoxSizer(wx.HORIZONTAL)
        self.panel.SetSizer(all_display)

        obj = __import__('pyslip', globals(), locals(), ['stamen_transport'])
        tileset = getattr(obj, 'stamen_transport')
        tile_obj = tileset.Tiles()

        # put map view in left of horizontal box
        self.pyslip = pyslip.pySlip(self.panel, tile_src=tile_obj,
                                    style=wx.SIMPLE_BORDER)
        all_display.Add(self.pyslip, proportion=1, flag=wx.EXPAND)

        # add controls at right
        controls = self.make_gui_controls(self.panel)
        all_display.Add(controls, proportion=0)

        self.panel.SetSizerAndFit(all_display)

        self.pyslip.Bind(pyslip.EVT_PYSLIP_LEVEL, self.level_change_event)
        self.pyslip.Bind(pyslip.EVT_PYSLIP_POSITION, self.mouse_posn_event)
        self.pyslip.Bind(wx.EVT_RIGHT_DOWN, self.right_click_event)

        original_img = '550D_2020-08-28_IMG_7103.jpg'
        thumb_img = '550D_2020-08-28_IMG_7103.jpg.thumb'
        img = Image.open(original_img)
        img.thumbnail((64, 64), Image.ANTIALIAS)
        img.save('550D_2020-08-28_IMG_7103.jpg.thumb', "JPEG")
        ShipImg = thumb_img
        ImageData = [
                     (120.0, 24.0, ShipImg, {'placement': 'cc'}),
                     # Venus - 1826
                     (120.1, 24.1, ShipImg, {'placement': 'ne'}),
                     # Wolverine - 1879
                     (120.2, 24.2, ShipImg, {'placement': 'nw'}),
                     # Thomas Day - 1884
                     (120.3, 24.3, ShipImg, {'placement': 'sw'}),
                     # Sybil - 1902
                     (120.4, 24.4, ShipImg, {'placement': 'se'}),
                     # Prince of Denmark - 1863
                     (120.5, 24.5, ShipImg),
                     # Moltke - 1911
                     (120.6, 24.6, ShipImg)
                    ]
        MRShowLevels = [3, 4, 5, 6, 7, 8, 9, 10]
        self.image_layer = \
                self.pyslip.AddImageLayer(ImageData, map_rel=True,
                                          visible=True,
                                          delta=10,
                                          show_levels=MRShowLevels,
                                          name='<image_layer>')
        self.point_layer = None

        self.pyslip.GotoLevelAndPosition(8, (118.01, 26.01))
        self.last_clicked_loc = None

        self.Centre()
        self.Show()
        self.Maximize(True)

    def make_point_layer(self, long, lat):
        PointData = [(long, lat)]
        MRShowLevels = [3, 4, 5, 6, 7, 8, 9, 10]
        self.point_layer = \
                self.pyslip.AddPointLayer(PointData, map_rel=True,
                                          colour='#ff0000f0', radius=6,
                                          # offset points to exercise placement
                                          offset_x=0, offset_y=0, visible=True,
                                          show_levels=MRShowLevels,
                                          delta=40,
                                          placement='nw',   # check placement
                                          name='<pt_layer>')
    
    def make_gui_controls(self, parent):
        """Build the 'controls' part of the GUI

        parent  reference to parent

        Returns reference to containing sizer object.

        Should really use GridBagSizer layout.
        """

        # all controls in vertical box sizer
        controls = wx.BoxSizer(wx.VERTICAL)

        # put level and position into one 'controls' position
        tmp = wx.BoxSizer(wx.HORIZONTAL)
        tmp.AddSpacer(HorizSpacer)
        level = self.make_gui_level(parent)
        tmp.Add(level, proportion=0, flag=wx.EXPAND|wx.ALL)
        tmp.AddSpacer(HorizSpacer)
        mouse = self.make_gui_mouse(parent)
        tmp.Add(mouse, proportion=0, flag=wx.EXPAND|wx.ALL)
        tmp.AddSpacer(HorizSpacer)

        controls.Add(tmp, proportion=0, flag=wx.EXPAND|wx.ALL)
        controls.AddSpacer(VertSpacer)

        tmp = wx.BoxSizer(wx.HORIZONTAL)
        tmp.AddSpacer(HorizSpacer)
        self.file_list = wx.ListCtrl(parent, wx.ID_ANY, style = wx.LC_REPORT)
        self.file_list.InsertColumn(0, 'Path')
        tmp.Add(self.file_list, proportion=1, flag=wx.EXPAND|wx.ALL)
        tmp.AddSpacer(HorizSpacer)
        controls.Add(tmp, proportion=0, flag=wx.EXPAND|wx.ALL)
        controls.AddSpacer(VertSpacer)

        tmp = wx.BoxSizer(wx.HORIZONTAL)
        tmp.AddSpacer(HorizSpacer)
        open_file_btn = wx.Button(parent, wx.ID_ANY, 'Open')
        tmp.Add(open_file_btn, proportion=1, flag=wx.EXPAND|wx.ALL)
        tmp.AddSpacer(HorizSpacer)
        controls.Add(tmp, proportion=0, flag=wx.EXPAND|wx.ALL)
        controls.AddSpacer(VertSpacer)

        tmp = wx.BoxSizer(wx.HORIZONTAL)
        tmp.AddSpacer(HorizSpacer)
        set_location_btn = wx.Button(parent, wx.ID_ANY, 'Set Location')
        tmp.Add(set_location_btn, proportion=1, flag=wx.EXPAND|wx.ALL)
        tmp.AddSpacer(HorizSpacer)
        controls.Add(tmp, proportion=0, flag=wx.EXPAND|wx.ALL)
        controls.AddSpacer(VertSpacer)

        open_file_btn.Bind(wx.EVT_BUTTON, self.open_file_clicked)
        set_location_btn.Bind(wx.EVT_BUTTON, self.set_location_clicked)

        return controls

    def make_gui_level(self, parent):
        """Build the control that shows the level.

        parent  reference to parent

        Returns reference to containing sizer object.
        """

        # create objects
        txt = wx.StaticText(parent, wx.ID_ANY, 'Level: ')
        self.map_level = ROTextCtrl(parent, '', size=(30,-1),
                                    tooltip='Shows map zoom level')

        # lay out the controls
        sb = AppStaticBox(parent, 'Map level')
        box = wx.StaticBoxSizer(sb, orient=wx.HORIZONTAL)
        box.Add(txt, flag=(wx.ALIGN_CENTER_VERTICAL |wx.LEFT))
        box.Add(self.map_level, proportion=0,
                flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL)

        return box

    def make_gui_mouse(self, parent):
        """Build the mouse part of the controls part of GUI.

        parent  reference to parent

        Returns reference to containing sizer object.
        """

        # create objects
        txt = wx.StaticText(parent, wx.ID_ANY, 'Lon/Lat: ')
        self.mouse_position = ROTextCtrl(parent, '', size=(120,-1),
                                         tooltip=('Shows the mouse '
                                                  'longitude and latitude '
                                                  'on the map'))

        # lay out the controls
        sb = AppStaticBox(parent, 'Mouse position')
        box = wx.StaticBoxSizer(sb, orient=wx.HORIZONTAL)
        box.Add(txt, flag=(wx.ALIGN_CENTER_VERTICAL |wx.LEFT))
        box.Add(self.mouse_position, proportion=0,
                flag=wx.RIGHT|wx.TOP|wx.BOTTOM)

        return box

    def mouse_posn_event(self, event):
        """Handle a "mouse position" event from the pySlipQt widget.
       
        The 'event' object has these attributes:
            event.etype  the type of event
            event.mposn  the new mouse position on the map (xgeo, ygeo)
            event.vposn  the new mouse position on the view (x, y)
        """

        if event.mposn:
            (lon, lat) = event.mposn
            # we clamp the lon/lat to zero here since we don't want small
            # negative values displaying as "-0.00"
            if abs(lon) < 0.01:
                lon = 0.0
            if abs(lat) < 0.01:
                lat = 0.0
            self.mouse_position.SetValue('%.2f/%.2f' % (lon, lat))
        else:
            self.mouse_position.SetValue('')
            
    def level_change_event(self, event):
        self.map_level.SetValue(str(event.level))

    def right_click_event(self, event):
        self.last_clicked_loc = self.pyslip.View2Geo(event.GetPosition())
        if self.point_layer != None:
            self.pyslip.DeleteLayer(self.point_layer)
        self.make_point_layer(self.last_clicked_loc[0], self.last_clicked_loc[1])

    def open_file_clicked(self, event):
        with wx.FileDialog(self, "Open files for geotagging", wildcard="Images (*.jpg)|*.jpg",
                       style=wx.FD_OPEN | wx.FD_MULTIPLE) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind

            paths = fileDialog.GetPaths()
            for p in paths:
                self.file_list.InsertItem(0, p)

    def set_location_clicked(self, event):
        if self.last_clicked_loc == None:
            wx.MessageBox('Please right-click to set location first', 'Info', wx.OK | wx.ICON_INFORMATION)
            return
        
        for i in range(self.file_list.GetItemCount()):
            file_to_process = self.file_list.GetItemText(i)
            print(file_to_process)

            lng_deg = to_deg(self.last_clicked_loc[0], ["W", "E"])
            lat_deg = to_deg(self.last_clicked_loc[1], ["S", "N"])
            exiv_lng = (change_to_rational(lng_deg[0]), change_to_rational(lng_deg[1]), change_to_rational(lng_deg[2]))
            exiv_lat = (change_to_rational(lat_deg[0]), change_to_rational(lat_deg[1]), change_to_rational(lat_deg[2]))

            im = Image.open(file_to_process)
            exif_dict = piexif.load(im.info["exif"])
            exif_dict["GPS"] = {
                piexif.GPSIFD.GPSVersionID: (2, 0, 0, 0),
                piexif.GPSIFD.GPSAltitudeRef: 0,
                piexif.GPSIFD.GPSAltitude: (1, 1),
                piexif.GPSIFD.GPSLatitudeRef: lat_deg[3],
                piexif.GPSIFD.GPSLatitude: exiv_lat,
                piexif.GPSIFD.GPSLongitudeRef: lng_deg[3],
                piexif.GPSIFD.GPSLongitude: exiv_lng,
            }
            
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, file_to_process)
    
app = wx.App()
app_frame = AppFrame()
app_frame.Show()
app.MainLoop()

for f in glob.glob('*.thumb'):
    os.remove(f)
