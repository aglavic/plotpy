# -*- encoding: utf-8 -*-
'''
  Main window user interface class for all sessions.
'''

import os
import gtk
import gobject
from main_window_actions import apihelp
from plot_script.config import gui as gui_config
from autodialogs import FunctionHandler


__author__="Artur Glavic"
__credits__=['Liane Schätzler', 'Emmanuel Kentzinger', 'Werner Schweika',
              'Paul Zakalek', 'Eric Rosén', 'Daniel Schumacher', 'Josef Heinen']
from plot_script.plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Production"

class MainUI(object):
  '''
    User Interface (Menu Toolbar) for the main window.
  '''

  #+++++++++++++++++++++Functions responsible for menus and toolbar++++++++++++++++++++++#

  def build_menu(self):
    '''
      Create XML text for the menu and toolbar creation. In addition the variable
      actions are stored in a list. (See __create_action_group function)
      The XML text is used for the UIManager to create the bars,for more 
      information see the pygtk documentation for the UIManager.
      
      :return: XML string for all menus and toolbar.
    '''
    self.added_items=(("xMenu", None, # name, stock id
        "_x-axis", None, # label, accelerator
        "xMenu", # tooltip
        None),
        ("yMenu", None, # name, stock id
        "_y-axis", None, # label, accelerator
        "yMenu", # tooltip
        None),
    ("zMenu", None, # name, stock id
        "_z-axis", None, # label, accelerator
        "zMenu", # tooltip
        None),
    ("y2Menu", None, # name, stock id
        "y2-axis", None, # label, accelerator
        "y2Menu", # tooltip
        None),
    ("dyMenu", None, # name, stock id
        "_error", None, # label, accelerator
        "dyMenu", # tooltip
        None),
    ("Profiles", None, # name, stock id
        "_Profiles", None, # label, accelerator
        "Load or save a plot profile", # tooltip
        None),
    ("SaveProfile", None, # name, stock id
        "Save Profile", None, # label, accelerator
        "Save a plot profile", # tooltip
        self.save_profile),
    ("DeleteProfile", None, # name, stock id
        "Delete Profile", None, # label, accelerator
        "Delete a plot profile", # tooltip
        self.delete_profile),
    ("x-number", None, # name, stock id
        "Point Number", None, # label, accelerator
        None, # tooltip
        self.change),
    ("y-number", None, # name, stock id
        "Point Number", None, # label, accelerator
        None, # tooltip
        self.change),
    ("FilesMenu", None, # name, stock id
        "Change", None, # label, accelerator
        None, # tooltip
        None),)
  # Menus allways present
    output='''<ui>
    <menubar name='MenuBar'>
      <menu action='FileMenu'>
        <menuitem action='OpenDatafile'/>
        <menuitem action='SaveGPL'/>
        <menu action='SnapshotSub'>
          <menuitem action='SaveSnapshot'/>
          <menuitem action='SaveSnapshotAs'/>
          <menuitem action='SaveSnapshotNumpy'/>
          <menuitem action='LoadSnapshot'/>
          <menuitem action='LoadSnapshotFrom'/>
        </menu>
        <separator name='static14'/>
        <menuitem action='Export'/>
        <menuitem action='ExportAs'/>
        <menuitem action='ExportAll'/>
        <menuitem action='ToClipboard'/>
        <separator name='static1'/>
        <menuitem action='Print'/>
        <menuitem action='PrintAll'/>
        <separator name='static15'/>
        <menuitem action='ChangeSession'/>
        <menuitem action='TransfereDatasets'/>
        <separator name='static2'/>
        <menuitem action='Quit'/>
      </menu>
      <menu action='FilesMenu'>
      '''
    for i, name in enumerate([ds[0] for ds in sorted(self.active_session.file_data.items())]):
      output+="        <menuitem action='File-"+str(i)+"'/>\n"
      self.added_items+=(("File-"+str(i), None,
                          os.path.split(name)[1],
                          None, None, self.change_active_file),)
    output+='''
      </menu>
      <separator name='static12'/>
      <menu action='ViewMenu'>
        <menu action='AxesMenu'>
      '''
    if len(self.measurement)>0:
      # Menus for column selection created depending on input measurement
      if self.active_multiplot:
        columns=[(i, col.dimension) for i, col in enumerate(self.multiplot[0][0].data)]
        for dataset, ignore in self.multiplot:
          columnsi=dataset.dimensions()
          for item in reversed(columns):
            if not item[1] in columnsi:
              columns.remove(item)
      else:
        columns=[(i, col.dimension) for i, col in enumerate(self.active_dataset.data)]
      output+='''
            <menu action='xMenu'>
              <menuitem action='x-number'/>
        '''
      for i, dimension in columns:
        output+="         <menuitem action='x-"+str(i)+"'/>\n"
        self.added_items=self.added_items+(("x-"+str(i), None, dimension, None, None, self.change),)
      output+='''
            </menu>
            <menu action='yMenu'>
              <menuitem action='y-number'/>
        '''
      for i, dimension in columns:
        output+="            <menuitem action='y-"+str(i)+"'/>\n"
        self.added_items=self.added_items+(("y-"+str(i), None, dimension, None, None, self.change),)
      if self.active_dataset.zdata>=0:
        output+='''
              </menu>
              <placeholder name='zMenu'>
              <menu action='zMenu'>
          '''
        for i, dimension in columns:
          output+="          <menuitem action='z-"+str(i)+"'/>\n"
          self.added_items=self.added_items+(("z-"+str(i), None, dimension, None, None, self.change),)
        if hasattr(self.active_dataset, 'y2data') and \
           self.active_dataset.y2data>=0:
          output+='''
                </menu>
                <menu action='y2Menu'>
            '''
          for i, dimension in columns:
            output+="          <menuitem action='y2-"+str(i)+"'/>\n"
            self.added_items=self.added_items+(("y2-"+str(i), None, dimension, None, None, self.change),)
        output+="</menu>\n</placeholder>\n"
      else:
        output+='''
              </menu>      
              <placeholder name='zMenu'/>'''
      #output+='''
      #      <menu action='dyMenu'>
      #  '''
      #for i, dimension in enumerate(self.active_dataset.dimensions()):
      #  output+="              <menuitem action='dy-"+str(i)+"'/>\n"
      #  self.added_items=self.added_items+(("dy-"+str(i), None, dimension, None, None, self.change),)
      # allways present stuff and toolbar
      #output+='''                   </menu>'''
    output+='''
        </menu>
        <menu action='Profiles'>
      '''
    for name in sorted(self.profiles.items()):
      output+="        <menuitem action='"+\
        name[0]+"' position='top'/>\n"
      self.added_items+=((name[0], None, '_'+name[0], None, None, self.load_profile),)
    output+='''  <separator name='static8'/>
          <menuitem action='SaveProfile' position="bottom"/>
          <menuitem action='DeleteProfile' position="bottom"/>
        </menu>
        <separator name='static9'/>
        <menu action='MultiplotMenu'>
          <menuitem action='Multiplot'/>
          <menuitem action='AddMultiplot'/>
          <menuitem action='AddAllMultiplot'/>
          <menuitem action='ToggleMultiplotCopymode'/>
          <menuitem action='NewMultiplot'/>
          <menuitem action='ClearMultiplot'/>
        </menu>
        <menu action='Navigate'>
          <menuitem action='Next'/>
          <menuitem action='Prev'/>
          <menuitem action='First'/>
          <menuitem action='Last'/>
          <menuitem action='Up'/>
          <menuitem action='Down'/>
        </menu>
        <menu action='PlotAppearance'>
          <menuitem action='Apply'/>
          <separator name='static3'/>
          <menuitem action='PlotKeyLeft'/>
          <menuitem action='PlotKeyRight'/>
          <menuitem action='PlotKeyBottomLeft'/>
          <menuitem action='PlotKeyBottomRight'/>
          <separator name='static31'/>
          <menuitem action='PlotToggleGrid'/>
          '''
    if len(self.measurement)>0 and self.active_dataset.zdata>=0:
      output+='''<menuitem action='XYProjections'/>
        '''
    else:
      output+='''<menuitem action='PlotToggleLinespoints'/>
        <menuitem action='ErrorBars'/>
        '''
    output+='''<separator name='static32'/>
      '''
    if len(self.measurement)==0 or self.active_dataset.zdata>=0:
      output+='''<menuitem action='SelectColor'/>
        '''
    else:
      output+='''<menuitem action='ChangeStyle'/>
        '''
    output+='''<menuitem action='ChangeXYZLabel'/>
          <menuitem action='LabelsArrows'/>
        </menu>
        <separator name='static4'/>
        <menuitem action='ShowPlotTree'/>
        <menuitem action='ShowPlotparams'/>
        <menuitem action='ShowImportInfo'/>
        <menuitem action='ShowNotebook'/>
      </menu>
      <menu action='TreatmentMenu'>
        '''
    #++++++++++++++ create session specific menu ++++++++
    specific_menu_items=self.active_session.create_menu()
    output+=specific_menu_items[0]
    self.session_added_items=specific_menu_items[1]
    #-------------- create session specific menu --------
    if len(self.measurement)>0:
      output+='''
          <menuitem action='FitData'/>
          <placeholder name='MultiFitData'/>
          <separator name='static5'/>
          <menuitem action='FilterData'/>
          <menuitem action='TransformData'/>
          <separator name='TreatmentStatic'/>'''
      if self.active_dataset.zdata>=0:
        output+='''
          <placeholder name='z-actions'>
          <menuitem action='CrossSection'/>
          <menuitem action='RadialIntegration'/>
          <menuitem action='IntegrateIntensities'/>
          <separator name='z-sep1'/>
          <menuitem action='InterpolateSmooth'/>
          <menuitem action='RebinData'/>
          </placeholder>        
          <placeholder name='y-actions'/>'''
      else:
        output+='''
          <placeholder name='z-actions'/>
          <placeholder name='y-actions'>
          <menuitem action='CombinePoints'/>
          <menu action='SimpleCorrections'>
            <menuitem action='XYOffset'/>
            <menuitem action='Normalize'/>
          </menu>
          <menuitem action='Integrate'/>
          <menuitem action='Derivate'/>
          <menuitem action='PeakInfo'/>
          <menu action='PeakFinderMenu'>
            <menuitem action='PeakFinderDialog'/>
            <menu action='PeakPresetSummary'>
              <menuitem action='PeakPresetSummary-1'/>
              <menuitem action='PeakPresetSummary-2'/>
              <menuitem action='PeakPresetSummary-3'/>
              <menuitem action='PeakPresetSummary-4'/>
              <menuitem action='PeakPresetSummary-5'/>
            </menu>
            <menu action='PeakPresetFit'>
              <menuitem action='PeakPresetFit-1'/>
              <menuitem action='PeakPresetFit-2'/>
              <menuitem action='PeakPresetFit-3'/>
              <menuitem action='PeakPresetFit-4'/>
              <menuitem action='PeakPresetFit-5'/>
            </menu>
          </menu>
          <menuitem action='ColorcodePoints'/>
          </placeholder>'''
    output+='''
        <separator name='static6'/>
        <menuitem action='RemovePlot'/>
      </menu>
      <menu action='ExtrasMenu'>
        <menuitem action='Makro'/>
        <menuitem action='LastMakro'/>
        <menuitem action='History'/>
        <menuitem action='OpenConsole'/>
        <separator name='extras1'/>
        <menuitem action='OpenDataView'/>
        <separator name='extras2'/>
        <menuitem action='ConnectIPython'/>
        <separator name='extras3'/>
        <menuitem action='EditUserConfig'/>
      </menu>
      <separator name='static13'/>
      <menu action='HelpMenu'>
        <menuitem action='ShowConfigPath'/>
        <menuitem action='APIReference'/>
        <menuitem action='CheckForUpdate'/>
      <separator name='help1'/>
        <menuitem action='About'/>
        '''
    if self.active_session.DEBUG:
      output+='''
      '''
    plugin_menu=''
    for plugin in self.active_session.plugins:
      if hasattr(plugin, 'menu') and ('all' in plugin.SESSIONS or self.active_session.__class__.__name__ in plugin.SESSIONS):
        string, actions=plugin.menu(self, self.active_session)
        plugin_menu+=string
        self.session_added_items=self.session_added_items+actions
    if plugin_menu!='':
      output+='''
        </menu>
        <menu action='PluginMenu'>
      '''+plugin_menu
      self.session_added_items=self.session_added_items+(("PluginMenu", None, "Plugins", None, None, None),)
    output+=FunctionHandler.get_menu_string()
    self.session_added_items=self.session_added_items+FunctionHandler.get_menu_actions()
    output+='''
      </menu>
    </menubar>
    <toolbar  name='ToolBar1'>
      <toolitem action='First'/>
      <toolitem action='Prev'/>
      <toolitem action='Next'/>
      <toolitem action='Last'/>
      <separator name='static10'/>
      <toolitem action='Apply'/>
      <toolitem action='PlotToggleGrid'/>
      '''
    if len(self.measurement)>0 and self.active_dataset.zdata>=0:
      output+='''<toolitem action='XYProjections'/>
      '''
    else:
      output+='''<toolitem action='PlotToggleLinespoints'/>
      <toolitem action='ErrorBars'/>
      '''
    output+='''<toolitem action='ToggleMousemode' />
      <separator name='static11'/>
      <toolitem action='AddMultiplot'/>
      <toolitem action='Multiplot'/>
      <separator name='static12'/>
      <toolitem action='ExportAll'/>
      <toolitem action='SaveSnapshot'/>
      <toolitem action='LoadSnapshot'/>
      <separator name='static13'/>
      <toolitem action='ShowPersistent'/>
      '''
    if len(self.measurement)>0 and self.active_dataset.zdata>=0 and len(self.active_dataset.plot_together)>1:
      output+='''      <toolitem action='TogglePlotFit'/>
      <toolitem action='IteratePlotFit'/>'''
    output+='''
    </toolbar>
    <toolbar name='ToolBar2'>
    </toolbar>
    </ui>'''
    return output

  def create_action_group(self):
    '''
      Create actions for menus and toolbar.
      Every entry creates a gtk.Action and the function returns a gtk.ActionGroup.
      When the action is triggered it calls a function.
      For more information see the pygtk documentation for the UIManager and ActionGroups.
      
      :return: ActionGroup for all menu entries.
    '''
    entries=(
      ("FileMenu", None, "_File"), # name, stock id, label
      ("ViewMenu", None, "_View"), # name, stock id, label
      ("AxesMenu", None, "_Axes"), # name, stock id, label
      ("TreatmentMenu", None, "_Data treatment"), # name, stock id, label
      ("ExtrasMenu", None, "Extras"), # name, stock id, label
      ("HelpMenu", None, "_Help"), # name, stock id, label
      ("ToolBar1", None, "Toolbar1"), # name, stock id, label
      ("ToolBar2", None, "Toolbar2"), # name, stock id, label
      ("Navigate", None, "Navigate"), # name, stock id, label
      ("OpenDatafile", gtk.STOCK_OPEN, # name, stock id
        "_Open File", "<control>O", # label, accelerator
        "Open a new datafile", # tooltip
        self.add_file),
      ("SnapshotSub", gtk.STOCK_EDIT, # name, stock id
        "Snapshots", None, # label, accelerator
        None, None), # tooltip
      ("SaveSnapshot", gtk.STOCK_EDIT, # name, stock id
        "Save Snapshot", "<alt>S", # label, accelerator
        "Save the current state for this measurement as Snapshot (ALT+S)", # tooltip
        self.save_snapshot),
      ("SaveSnapshotAs", gtk.STOCK_EDIT, # name, stock id
        "Save Snapshot As...", "<alt><shift>S", # label, accelerator
        "Save the current state for this measurement as Snapshot.", # tooltip
        self.save_snapshot),
      ("SaveSnapshotNumpy", None, # name, stock id
        "Save Dataset As Numpy Archive...", "<alt><shift>N", # label, accelerator
        "Save the current state for this dataset.", # tooltip
        self.save_snapshot),
      ("LoadSnapshot", gtk.STOCK_OPEN, # name, stock id
        "Load Snapshot", "<alt>O", # label, accelerator
        "Load a state for this measurement stored before (ALT+O)", # tooltip
        self.load_snapshot),
      ("LoadSnapshotFrom", gtk.STOCK_OPEN, # name, stock id
        "Load Snapshot From...", "<alt><shift>O", # label, accelerator
        "Load a state for this measurement stored before.", # tooltip
        self.load_snapshot),
      ("SaveGPL", gtk.STOCK_SAVE, # name, stock id
        "_Save this dataset (.out)...", "<control>S", # label, accelerator
        "Save Gnuplot and datafile", # tooltip
        self.export_plot),
      ("Export", gtk.STOCK_SAVE, # name, stock id
        "_Export (.png)", "<control>E", # label, accelerator
        "Export current Plot", # tooltip
        self.export_plot),
      ("ExportAs", gtk.STOCK_SAVE, # name, stock id
        "E_xport As (.png/.ps)...", '<control><shift>E', # label, accelerator
        "Export Plot under other name", # tooltip
        self.export_plot),
      ("Print", gtk.STOCK_PRINT, # name, stock id
        "_Print...", "<control>P", # label, accelerator
        None, # tooltip
        self.print_plot),
      ("PrintAll", gtk.STOCK_PRINT, # name, stock id
        "Print Selection...", "<control><shift>P", # label, accelerator
        None, # tooltip
        self.print_plot),
      ("ChangeSession", gtk.STOCK_LEAVE_FULLSCREEN, # name, stock id
        "Change Active Session...", None, # label, accelerator
        None, # tooltip
        self.change_session),
      ("TransfereDatasets", None, # name, stock id
        "Transfere Datasets to Session...", None, # label, accelerator
        None, # tooltip
        self.transfere_datasets),
      ("Quit", gtk.STOCK_QUIT, # name, stock id
        "_Quit", "<control>Q", # label, accelerator
        "Quit", # tooltip
        self.main_quit),
      ("About", None, # name, stock id
        "About", None, # label, accelerator
        "About", # tooltip
        self.activate_about),
      ("APIReference", None, # name, stock id
        "API Reference...", None, # label, accelerator
        "Open API reference manual in a webbrowser", # tooltip
        apihelp),
      ("ShowConfigPath", None, # name, stock id
        "Show Config Path...", None, # label, accelerator
        "Show Configfile Path", # tooltip
        self.show_config_path),
      ("History", None, # name, stock id
        "Action History", None, # label, accelerator
        "History", # tooltip
        self.action_history),
      ("Makro", None, # name, stock id
        "Run Makro...", None, # label, accelerator
        "Run Makro", # tooltip
        self.run_action_makro),
      ("LastMakro", None, # name, stock id
        "Run Last Makro", "<control>R", # label, accelerator
        "Run Last Makro", # tooltip
        self.run_last_action_makro),
      ("First", gtk.STOCK_GOTO_FIRST, # name, stock id
        "First", "<control><shift>B", # label, accelerator
        "First Plot (CTRL+SHIFT+B)", # tooltip
        self.iterate_through_measurements),
      ("Prev", gtk.STOCK_GO_BACK, # name, stock id
        "Prev", "<control>B", # label, accelerator
        "Previous Plot (CTRL+B)", # tooltip
        self.iterate_through_measurements),
      ("Next", gtk.STOCK_GO_FORWARD, # name, stock id
        "_Next", "<control>N", # label, accelerator
        "Next Plot (CTRL+N)", # tooltip
        self.iterate_through_measurements),
      ("Down", gtk.STOCK_GO_DOWN, # name, stock id
        "Down", "<control>J", # label, accelerator
        "Previous File", # tooltip
        self.iterate_through_measurements),
      ("Up", gtk.STOCK_GO_UP, # name, stock id
        "Up", "<control>H", # label, accelerator
        "Next File", # tooltip
        self.iterate_through_measurements),
      ("Last", gtk.STOCK_GOTO_LAST, # name, stock id
        "Last", "<control><shift>N", # label, accelerator
        "Last Plot (CTRL+SHIFT+N)", # tooltip
        self.iterate_through_measurements),
      ("ShowPlotparams", None, # name, stock id
        "Show plot parameters", None, # label, accelerator
        "Show the gnuplot parameters used for plot.", # tooltip
        self.show_last_plot_params),
      ("ShowImportInfo", None, # name, stock id
        "Show File Import Informations", None, #'i',                     # label, accelerator
        "Show the information from the file import in this session.", # tooltip
        self.show_status_dialog),
      ("ShowNotebook", None, # name, stock id
        "Show Extra Drop Notebook Dialog", '<control><shift>T', #'i',                     # label, accelerator
        "Show a dialog that allows to drop the plot tab etc.", # tooltip
        self.open_tabdialog),
      ("ShowPlotTree", None, # name, stock id
        "Show Tree of Datasets", "<control>T", #'i',                     # label, accelerator
        "Show Tree of Datasets...", # tooltip
        self.show_plot_tree),
      ("ChangeStyle", None, # name, stock id
        "Change Plot Style", '<control>Y', # label, accelerator
        None, # tooltip
        self.change_plot_style),
      ("ChangeXYZLabel", None, # name, stock id
        "Change Plot XYZ-Labels", '<control><shift>L', # label, accelerator
        None, # tooltip
        self.change_xyzaxis_style),
      ("LabelsArrows", None, # name, stock id
        "Labels and Arrows ...", '<control>L', # label, accelerator
        None, # tooltip
        self.open_label_arrows_dialog),
      ("FilterData", None, # name, stock id
        "Filter the data points", None, #'f',                     # label, accelerator
        None, # tooltip
        self.change_data_filter),
      ("TransformData", None, # name, stock id
        "Transform the Units/Dimensions", None, #'t',                     # label, accelerator
        None, # tooltip
        self.unit_transformation),
      ("CrossSection", None, # name, stock id
        "Cross-Section...", '<alt>C', #'s',                     # label, accelerator
        None, # tooltip
        self.extract_cross_section),
      ("InterpolateSmooth", None, # name, stock id
        "Interpolate to regular grid...", "<control>G", # label, accelerator
        None, # tooltip
        self.interpolate_and_smooth_dialog),
      ("RebinData", None, # name, stock id
        "Rebin data...", "<control><shift>G", # label, accelerator
        None, # tooltip
        self.rebin_3d_data_dialog),
      ("RadialIntegration", None, # name, stock id
        "Calculate Radial/Arc Integration...", "<alt>R", # label, accelerator
        None, # tooltip
        self.extract_radial_integration),
      ("IntegrateIntensities", None, # name, stock id
        "Integrat Intensities...", None, # label, accelerator
        None, # tooltip
        self.extract_integrated_intensities),
      ("CombinePoints", None, # name, stock id
        "Combine points", '<alt>C', # label, accelerator
        None, # tooltip
        self.combine_data_points),
      ("SimpleCorrections", None, # name, stock id
        "Correct the Dataset", None, # label, accelerator
        None, # tooltip
        None),
      ("XYOffset", None, # name, stock id
        "xy-Offset", '<alt>X', # label, accelerator
        None, # tooltip
        self.correct_offset),
      ("Normalize", None, # name, stock id
        "Normalization", '<alt>N', # label, accelerator
        None, # tooltip
        self.normalize_data),
      ("Derivate", None, # name, stock id
        "Derivate or Smoothe", '<control>D', # label, accelerator
        None, # tooltip
        self.derivate_data),
      ("Integrate", None, # name, stock id
        "Integrate", '<control><shift>D', # label, accelerator
        None, # tooltip
        self.integrate_data),
      ("PeakInfo", None, # name, stock id
        "Generate Peak Info", "<alt><shift>I", # label, accelerator
        None, # tooltip
        self.peak_info),
      ("ColorcodePoints", None, # name, stock id
        "Show Colorcoded Points", None, # label, accelerator
        None, # tooltip
        self.colorcode_points),
      ("SelectColor", None, # name, stock id
        "Color Pattern...", None, #'p',                     # label, accelerator
        None, # tooltip
        self.change_color_pattern),
      ("Apply", gtk.STOCK_CONVERT, # name, stock id
        "Apply", None, #'a',                     # label, accelerator
        "Apply current plot settings to selected sequences", # tooltip
        self.apply_to_all),
      ("ExportAll", gtk.STOCK_EXECUTE, # name, stock id
        "Exp. Selection...", "<alt><shift>E", # label, accelerator
        "Export a selection of plots (ALT+SHIFT+E)", # tooltip
        self.export_plot),
      ("ToClipboard", gtk.STOCK_PASTE, # name, stock id
        "Copy Data to Clipboard", "<control><shift>C", # label, accelerator
        None, # tooltip
        self.export_clipboard),
      ("ErrorBars", gtk.STOCK_ADD, # name, stock id
        "E.Bars", "<alt>E", #'e',                     # label, accelerator
        "Toggle errorbars (ALT+E)", # tooltip
        self.toggle_error_bars),
      ("XYProjections", gtk.STOCK_FULLSCREEN, # name, stock id
        "XY-Proj.", None, #'e',                     # label, accelerator
        "Toggle xy-projections", # tooltip
        self.toggle_xyprojections),
      ("Multiplot", gtk.STOCK_YES, # name, stock id
        "Toggle Multiplot", '<control>M', #'m',                     # label, accelerator
        "Switch between Multiplot and Singleplot mode (CTRL+M)", # tooltip
        self.export_plot),
      ("MultiplotMenu", None, # name, stock id
        "Multiplot", None, # label, accelerator
        "Multiplot", # tooltip
        None),
      ("AddMultiplot", gtk.STOCK_JUMP_TO, # name, stock id
        "_Add", '<alt>a', # label, accelerator
        "Add Plot to Multiplot List (ALT+A)", # tooltip
        self.add_multiplot),
      ("AddAllMultiplot", gtk.STOCK_JUMP_TO, # name, stock id
        "Add all to Multiplot", '<alt><shift>a', # label, accelerator
        "Add all sequences to Multiplot List", # tooltip
        self.add_multiplot),
      ("ToggleMultiplotCopymode", gtk.STOCK_COPY, # name, stock id
        "Toggle Copy-Mode", '<control><alt>m', # label, accelerator
        "New items are copied when inserted", # tooltip
        self.toggle_multiplot_copymode),
      ("ClearMultiplot", gtk.STOCK_DELETE, # name, stock id
        "Clear Multiplot List", '<control><alt>a', #'c',                     # label, accelerator
        "Remove all multi-plot list entries", # tooltip
        self.add_multiplot),
      ("NewMultiplot", gtk.STOCK_NEW, # name, stock id
        "Add to New Multiplot List", '<control><shift>M', #'c',                     # label, accelerator
        "Create a new Multiplot List and add the active plot", # tooltip
        self.add_multiplot),
      ("RemovePlot", None, # name, stock id
        "Remove the active Plot (no way back!)", None, # label, accelerator
        "Remove the active Plot (no way back!)", # tooltip
        self.remove_active_plot),
      ("FitData", None, # name, stock id
        "_Fit data...", "<control>F", # label, accelerator
        "Dialog for fitting of a function to the active dataset.", # tooltip
        self.fit_dialog),
      ("MultiFitData", None, # name, stock id
        "Fit _Multiple datasets...", None, # label, accelerator
        "Dialog for fitting of a function to the active dataset.", # tooltip
        self.multi_fit_dialog),
      ("MultiplotExport", None, # name, stock id
        "Export Multi-plots", None, # label, accelerator
        "Export Multi-plots", # tooltip
        self.export_plot),
      ("OpenConsole", None, # name, stock id
        "Open IPython Console", "<control>I", # label, accelerator
        None, # tooltip
        self.open_ipy_console),
      ("OpenDataView", None, # name, stock id
        "Show/Edit Data", "<control><alt>D", # label, accelerator
        None, # tooltip
        self.open_dataview_dialog),
      ("ConnectIPython", None, # name, stock id
        "IP-Cluster...", None, # label, accelerator
        None, # tooltip
        self.connect_cluster),
      ("EditUserConfig", None, # name, stock id
        "Edit User Config", None, # label, accelerator
        None, # tooltip
        self.edit_user_config),
      ("ShowPersistent", gtk.STOCK_FULLSCREEN, # name, stock id
        "Open Persistent Gnuplot Window", "<alt>P", # label, accelerator
        "Open Persistent Gnuplot Window (ALT+P)", # tooltip
        self.plot_persistent),
      ("ToggleMousemode", gtk.STOCK_GOTO_TOP, # name, stock id
        "Toggle Mousemode", None, # label, accelerator
        "Switch mouse navigation On/Off (Off speeds up map plots)", # tooltip
        self.toggle_mouse_mode),
      ("TogglePlotFit", gtk.STOCK_ZOOM_FIT, # name, stock id
        "Toggle between data,fit and combined plot", "<control><shift>T", # label, accelerator
        "Toggle between data,fit and combined plot (CTRL+SHIFT+T)", # tooltip
        self.toggle_plotfit),
      ("IteratePlotFit", gtk.STOCK_ZOOM_100, # name, stock id
        "Select between data and fits to plot", None, # label, accelerator
        "Select between data and fits to plot", # tooltip
        self.toggle_plotfit),
      ("CheckForUpdate", None, # name, stock id
        "Check for Update", None, # label, accelerator
        "Check for Update", # tooltip
        self.check_for_updates),
      ("PlotAppearance", None,
        "Plot Appearance", None,
        "Plot Appearance",
        None),
      ("PlotKeyLeft", None, # name, stock id
        "Key on top left", 'F7', # label, accelerator
        "Key on top left", # tooltip
        self.change_plot_appearance),
      ("PlotKeyRight", None, # name, stock id
        "Key on top right", 'F8', # label, accelerator
        "Key on top right", # tooltip
        self.change_plot_appearance),
      ("PlotKeyBottomLeft", None, # name, stock id
        "Key on bottom left", '<shift>F7', # label, accelerator
        "Key on bottom left", # tooltip
        self.change_plot_appearance),
      ("PlotKeyBottomRight", None, # name, stock id
        "Key on bottom right", '<shift>F8', # label, accelerator
        "Key on bottom right", # tooltip
        self.change_plot_appearance),
      ("PlotToggleGrid", None, # name, stock id
        "Toggle grid", 'F9', # label, accelerator
        "Toggle grid [None>Major>Minor>Major-Front>Minor-Front] (F9)", # tooltip
        self.change_plot_appearance),
      ("PlotToggleLinespoints", None, # name, stock id
        "Toggle lines/linespoints", 'F6', # label, accelerator
        "Toggle lines/linespoints (F6)", # tooltip
        self.change_plot_appearance),

    )+self.added_items+self.peak_finder_presets();
    # Create the menubar and toolbar
    action_group=gtk.ActionGroup("AppWindowActions")
    action_group.add_actions(entries)
    action_group.add_actions(self.session_added_items, self)
    return action_group

  def peak_finder_presets(self):
    output=(
     ("PeakFinderMenu", None, # name, stock id
        "CWT Peak Finder", None, # label, accelerator
        None, # tooltip
        None),
     ("PeakPresetSummary", None, # name, stock id
        "Detect and show Summary", None, # label, accelerator
        None, # tooltip
        None),
     ("PeakPresetFit", None, # name, stock id
        "Detect and add Fits", None, # label, accelerator
        None, # tooltip
        None),
      ("PeakFinderDialog", None, # name, stock id
        "Find Peaks...", '<control>0', # label, accelerator
        None, # tooltip
        self.peak_finder),
      )
    for i in range(5):
      output=output+(
       ("PeakPresetSummary-%i"%(i+1), None, # name, stock id
        "Use Preset %i"%(i+1), '<control>%i'%(i+1), # label, accelerator
        None, # tooltip
        self.peak_finder),
       ("PeakPresetFit-%i"%(i+1), None, # name, stock id
        "Use Preset %i"%(i+1), '<control><alt>%i'%(i+1), # label, accelerator
        None, # tooltip
        self.peak_finder),
       )
    return output



  def rebuild_menus(self):
    '''
      Build new menu and toolbar structure.
    '''
    ui_info=self.build_menu() # build structure of menu and toolbar
    # remove old menu
    self.UIManager.remove_ui(self.toolbar_ui_id)
    self.UIManager.remove_action_group(self.toolbar_action_group)
    self.toolbar_action_group=self.create_action_group()
    self.UIManager.insert_action_group(self.toolbar_action_group, 0) # create action groups for menu and toolbar
    try:
        self.toolbar_ui_id=self.UIManager.add_ui_from_string(ui_info)
    except gobject.GError, msg:
        print "building menus failed: %s"%msg
    for item in gui_config.ICONS.items():
      self.replace_icon(*item)


  def replace_icon(self, item, imgfile):
    '''
      Cange the icon of one toolbar button to a user defined file.
      The file gets scaled to fit in a 24x24 pix button.
    '''
    size=float(gui_config.ICON_SIZE)
    path=self.active_session.SCRIPT_PATH
    icon=os.path.join(path, 'gtkgui', 'icons', imgfile)
    buf=gtk.gdk.pixbuf_new_from_file(icon)
    width=buf.get_width()
    height=buf.get_height()
    scale=min(size/width, size/height)
    buf=buf.scale_simple(int(width*scale), int(height*scale), gtk.gdk.INTERP_BILINEAR)

    for i in range(2):
      toolbutton=self.UIManager.get_widget('/ui/ToolBar%i/'%(i+1)+item)
      if toolbutton is not None:
        img=gtk.Image()
        img.set_from_pixbuf(buf)
        img.show()
        toolbutton.set_icon_widget(img)
    for menu in ['FileMenu', 'ViewMenu/ToolbarActions',
                 'FileMenu/SnapshotSub', 'ViewMenu/MultiplotMenu',
                 'ViewMenu/PlotAppearance',
                 ]:
      menuitem=self.UIManager.get_widget('/ui/MenuBar/'+menu+'/'+item)
      if menuitem is not None:
        img=gtk.Image()
        img.set_from_pixbuf(buf)
        img.show()
        menuitem.set_image(img)

  #---------------------Functions responsible for menus and toolbar----------------------#

  def show_add_info(self, action):
    '''
      Show or hide advanced options widgets.
    '''
    self.x_range_in.show()
    self.x_range_label.show()
    self.y_range_in.show()
    self.y_range_label.show()
    self.font_size.show()
    self.logx.show()
    self.logy.show()
    self.plot_options_button.show()
    if self.active_dataset.zdata>=0:
      self.logz.show()
      self.z_range_in.show()
      self.z_range_label.show()
      self.view_left.show()
      self.view_up.show()
      self.view_down.show()
      self.view_right.show()
    else:
      self.logz.hide()
      self.z_range_in.hide()
      self.z_range_label.hide()
      self.view_left.hide()
      self.view_up.hide()
      self.view_down.hide()
      self.view_right.hide()
    if hasattr(self.active_dataset, 'y2data') and self.active_dataset.y2data>=0:
      self.y2_slicing.show()
      self.y2_center.show()
      self.y2_width.show()
      self.grid_4dx.show()
      self.grid_4dy.show()
      ds=self.active_dataset
      if ds.slice_center is not None and ds.slice_width is not None:
        self.y2_width.set_sensitive(True)
        self.y2_width.set_text("%g"%ds.slice_width)
        self.y2_center.set_sensitive(True)
        self.y2_center.set_range(ds.y2.min(), ds.y2.max())
        self.y2_center.set_value(ds.slice_center)
        from math import log10
        self.y2_center.set_digits(int(max(0,-log10(ds.y2.max())))+2)
      else:
        self.y2_center.set_sensitive(False)
        self.y2_width.set_sensitive(False)
    else:
      self.y2_slicing.hide()
      self.y2_center.hide()
      self.y2_width.hide()
      self.grid_4dx.hide()
      self.grid_4dy.hide()

