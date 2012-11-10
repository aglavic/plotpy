# -*- encoding: utf-8 -*-
'''
  Main window action class for file import/export.
'''

import os
import sys
import gtk
import subprocess
from diverse_classes import PlotProfile
from dialogs import FileImportDialog, ExportFileChooserDialog, \
                    PreviewDialog, ImportWizard
from message_dialog import GUIMessenger
from plotpy import plotting
from plotpy.fio import reader, ascii
from plotpy.config import gnuplot_preferences
from plotpy.configobj import ConfigObj
import main_window_plotting

__author__="Artur Glavic"
__credits__=['Liane Schätzler', 'Emmanuel Kentzinger', 'Werner Schweika',
              'Paul Zakalek', 'Eric Rosén', 'Daniel Schumacher', 'Josef Heinen']
from plotpy.info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Production"

class MainFile(object):
  '''
    File Import/Export actions.
  '''

  def add_file(self, action=None, hide_status=True, file_names=None):
    '''
      Import one or more new datafiles of the same type.
      
      :return: List of names that have been imported.
    '''
    if file_names is None:
      #++++++++++++++++File selection dialog+++++++++++++++++++#
      #wildcards=self.active_session.FILE_WILDCARDS+\
      #          [(item[1][0], '*'+item[0]) for item in GENERIC_FORMATS.items()]
      wildcards=[['All Readers']+reader.types]
      if self.active_session.name in reader.sessions:
        session_readers=['%s Readers'%self.active_session.name]
        for readeri in reader.sessions[self.active_session.name]:
          for pattern in readeri.glob_patterns:
            if not pattern in session_readers:
              session_readers.append(pattern)
        wildcards.insert(0, session_readers+['*.mdd'])
      file_dialog=FileImportDialog(self.active_folder, wildcards)
      file_names, folder, template, ascii_filter=file_dialog.run()
      file_dialog.destroy()
      if file_names is None:
        # process canceled
        return
    else:
      folder=self.active_folder
      template=None
      ascii_filter=-3
    file_names=map(unicode, file_names)
    folder=unicode(folder)
    self.active_folder=folder
    #----------------File selection dialog-------------------#
    # show a status dialog for the file import
    if type(sys.stdout)!=file:
      if not self.status_dialog:
        status_dialog=GUIMessenger('Import Status',
                                  progressbar=self.progressbar,
                                  statusbar=self.statusbar,
                                  parent=self)
        self.status_dialog=status_dialog
        status_dialog.set_default_size(800, 600)
      else:
        status_dialog=self.status_dialog
      #status_dialog.show()
      sys.stdout.second_output=status_dialog
    # try to import the selected files and append them to the active session
    if template is None:
      if ascii_filter==-3:
        # normal import
        if self.active_session.ONLY_IMPORT_MULTIFILE:
          self.active_session.add_file(file_names, append=True)
        else:
          files_data=self.active_session.add_files(file_names, append=True)
          if len(files_data)>0:
            self.active_session.change_active(name=os.path.join(*files_data[0].origin))
          elif self.active_session.multiplots is not None:
            self.multiplot.new_from_list(self.active_session.multiplots)
            self.active_multiplot=True
      elif ascii_filter==-2:
        session=self.active_session
        # import with fitting filter_
        for file_name in file_names:
          file_type=file_name.rsplit('.', 1)[1]
          for filter_ in ascii.defined_filters:
            if file_type in filter_.file_types:
              ds=filter_.read_data(file_name)
              ds=session.create_numbers(ds)
              session.add_data(ds, file_name, True)
              session.new_file_data_treatment(ds)
              session.active_file_data=session.file_data[file_name]
              session.active_file_name=file_name
              break
      else:
        # import with new or selected filter_
        if ascii_filter==-1:
          filter_=self.new_ascii_import_filter(file_names[0])
          if filter_ is None:
            # Dialog was canceled
            if type(sys.stdout)!=file:
              sys.stdout.second_output=None
              #if hide_status:
              #  status_dialog.hide()
            return
          ascii.append_filter(filter_)
        else:
          filter_=ascii.defined_filters[ascii_filter]
        session=self.active_session
        for file_name in file_names:
          ds=filter_.read_data(file_name)
          ds=session.create_numbers(ds)
          session.add_data(ds, file_name, True)
          session.new_file_data_treatment(ds)
        session.active_file_data=session.file_data[file_names[0]]
        session.active_file_name=file_names[0]
    else:
      # if a template was selected, read the files using this template
      session=self.active_session
      for file_name in file_names:
        datasets=template(file_name)
        if datasets=='NULL':
          continue
        datasets=session.create_numbers(datasets)
        session.add_data(datasets, file_name)
        session.new_file_data_treatment(datasets)
      session.active_file_data=session.file_data[file_names[0]]
      session.active_file_name=file_names[0]
    # set the last imported file as active
    self.measurement=self.active_session.active_file_data
    if len(self.measurement)==0:
      # file was selected but without producing any result
      # this can only be triggered when importing at startup
      if type(sys.stdout)!=file:
        sys.stdout.second_output=None
        #if hide_status:
        #  status_dialog.hide()
      return True
    self.input_file_name=self.active_session.active_file_name
    self.index_mess=0
    self.plot_page_entry.set_width_chars(len(str(len(self.measurement)))+1)
    self.plot_page_entry.set_text('0')
    for window in self.open_windows:
      window.destroy()
    if type(sys.stdout)!=file:
      sys.stdout.second_output=None
      #if hide_status:
      #  status_dialog.hide()
    self.rebuild_menus()
    if hide_status:
      self.replot()
    if self.plot_tree is not None:
      self.plot_tree.add_data()
      self.plot_tree.set_focus_item(self.active_session.active_file_name, self.index_mess)
    return True

  def save_snapshot(self, action):
    '''
      Save a snapshot of the active work.
    '''
    if self.active_multiplot:
      if not action.get_name()=='SaveSnapshotAs':
        return
      multiplot=self.multiplot
      #++++++++++++++++File selection dialog+++++++++++++++++++#
      file_dialog=gtk.FileChooserDialog(title='Save Snapshot to File...',
                                        action=gtk.FILE_CHOOSER_ACTION_SAVE,
                                        buttons=(gtk.STOCK_SAVE, gtk.RESPONSE_OK,
                                                 gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
      file_dialog.set_select_multiple(False)
      file_dialog.set_default_response(gtk.RESPONSE_OK)
      file_dialog.set_current_folder(self.active_folder)
      filter_=gtk.FileFilter()
      filter_.set_name("Snapshots (*.mdd(.gz))")
      filter_.add_pattern("*.mdd")
      filter_.add_pattern("*.mdd.gz")
      file_dialog.add_filter(filter_)
      file_dialog.set_current_name(
            (multiplot.sample_name+'_'+multiplot.title+'.mdd').replace(' ', '')
                                  )
      filter_=gtk.FileFilter()
      filter_.set_name("All Files")
      filter_.add_pattern("*")
      file_dialog.add_filter(filter_)
      response=file_dialog.run()
      if response==gtk.RESPONSE_OK:
        self.active_folder=file_dialog.get_current_folder()
        name=unicode(file_dialog.get_filenames()[0], 'utf-8')
        if action.get_name()=='SaveSnapshotAs':
          if not (name.endswith(".mdd") or name.endswith(".mdd.gz")):
            name+=".mdd"
        self.active_session.multiplots=self.multiplot.get_list()
        self.active_session.store_snapshot(name, multiplots=True)
      file_dialog.destroy()
      #----------------File selection dialog-------------------#

      return
    if action.get_name()=='SaveSnapshot':
      name=None
    else:
      #++++++++++++++++File selection dialog+++++++++++++++++++#
      file_dialog=gtk.FileChooserDialog(title='Save Snapshot to File...',
                                        action=gtk.FILE_CHOOSER_ACTION_SAVE,
                                        buttons=(gtk.STOCK_SAVE, gtk.RESPONSE_OK,
                                                 gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
      file_dialog.set_select_multiple(False)
      file_dialog.set_default_response(gtk.RESPONSE_OK)
      file_dialog.set_current_folder(self.active_folder)
      if action.get_name()=='SaveSnapshotAs':
        filter_=gtk.FileFilter()
        filter_.set_name("Snapshots (*.mdd(.gz))")
        filter_.add_pattern("*.mdd")
        filter_.add_pattern("*.mdd.gz")
        file_dialog.add_filter(filter_)
        file_dialog.set_current_name(self.active_session.active_file_name+'.mdd')
      else:
        filter_=gtk.FileFilter()
        filter_.set_name("Numpy Archive (*.npz)")
        filter_.add_pattern("*.npz")
        file_dialog.add_filter(filter_)
        file_dialog.set_current_name(self.active_session.active_file_name+'.npz')
      filter_=gtk.FileFilter()
      filter_.set_name("All Files")
      filter_.add_pattern("*")
      file_dialog.add_filter(filter_)
      response=file_dialog.run()
      if response==gtk.RESPONSE_OK:
        self.active_folder=file_dialog.get_current_folder()
        name=unicode(file_dialog.get_filenames()[0], 'utf-8')
        if action.get_name()=='SaveSnapshotAs':
          if not (name.endswith(".mdd") or name.endswith(".mdd.gz")):
            name+=".mdd"
      elif response==gtk.RESPONSE_CANCEL:
        file_dialog.destroy()
        return False
      file_dialog.destroy()
      #----------------File selection dialog-------------------#
    if action.get_name()=='SaveSnapshotNumpy':
      self.active_dataset.export_npz(name)
    else:
      self.active_session.store_snapshot(name)

  def load_snapshot(self, action):
    '''
      Load a snapshot of earlier work.
    '''
    if action.get_name()=='LoadSnapshot':
      name=None
    else:
      #++++++++++++++++File selection dialog+++++++++++++++++++#
      file_dialog=gtk.FileChooserDialog(title='Load Snapshot from File...',
                                        action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                        buttons=(gtk.STOCK_OPEN, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
      file_dialog.set_select_multiple(False)
      file_dialog.set_default_response(gtk.RESPONSE_OK)
      file_dialog.set_current_folder(self.active_folder)
      filter_=gtk.FileFilter()
      filter_.set_name("Snapshots (*.mdd(.gz))")
      filter_.add_pattern("*.mdd")
      filter_.add_pattern("*.mdd.gz")
      file_dialog.add_filter(filter_)
      filter_=gtk.FileFilter()
      filter_.set_name("All Files")
      filter_.add_pattern("*")
      file_dialog.add_filter(filter_)
      response=file_dialog.run()
      if response==gtk.RESPONSE_OK:
        self.active_folder=file_dialog.get_current_folder()
        name=unicode(file_dialog.get_filenames()[0], 'utf-8')
        if not name.endswith(u".mdd") and not name.endswith(u".mdd.gz") :
          name+=u".mdd"
      elif response==gtk.RESPONSE_CANCEL:
        file_dialog.destroy()
        return False
      file_dialog.destroy()
      #----------------File selection dialog-------------------#
    loaded_multiplot=self.active_session.reload_snapshot(name)
    if loaded_multiplot:
      self.multiplot.new_from_list(self.active_session.multiplots)
      self.active_multiplot=True
    else:
      self.measurement=self.active_session.active_file_data
    self.replot()

  def export_clipboard(self, action):
    '''
      Export the active dataset as text to clipboard.
    '''
    clipboard=gtk.Clipboard(gtk.gdk.display_get_default(), "CLIPBOARD")
    data=self.active_dataset.get_filtered_data_matrix()
    items=map(lambda dataline: "\t".join(map(str, dataline)), data.transpose())
    clipboard_content="\n".join(items)
    header_cols=["%s[%s]"%(d, u) for d, u in zip(self.active_dataset.dimensions(),
                                                 self.active_dataset.units())]
    clipboard_header="# "+"\t".join(header_cols)+'\n'
    clipboard.set_text(clipboard_header+clipboard_content)

  def export_plot(self, action):
    '''
      Function for every export action. 
      Export is made as .png or .ps depending on the selected file name.
      Save is made as gnuplot file and output files.
    '''
    errorbars=main_window_plotting.errorbars
    self.active_session.picture_width='1600'
    self.active_session.picture_height='1200'
    if action.get_name()=='Multiplot':
      if len(self.multiplot)>0:
        self.active_multiplot=not self.active_multiplot
      else:
        self.active_multiplot=False
      self.rebuild_menus()
      return self.replot()
    if action.get_name()=='SaveGPL':
      #++++++++++++++++File selection dialog+++++++++++++++++++#
      file_dialog=gtk.FileChooserDialog(title='Save Gnuplot(.gp) and Datafiles(.out)...',
                                        action=gtk.FILE_CHOOSER_ACTION_SAVE,
                                        buttons=(gtk.STOCK_SAVE, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
      file_dialog.set_do_overwrite_confirmation(True)
      file_dialog.set_default_response(gtk.RESPONSE_OK)
      file_dialog.set_current_folder(self.active_folder)
      if self.active_multiplot:
        file_dialog.set_current_name((self.multiplot.sample_name+'_'+
                              self.multiplot.title+'_.gp').replace(' ', ''))
      else:
        file_dialog.set_current_name(os.path.split(self.active_session.active_file_name+'_.gp')[1])
      # create the filters in the file selection dialog
      filter_=gtk.FileFilter()
      filter_.set_name("Gnuplot (.gp)")
      filter_.add_pattern("*.gp")
      file_dialog.add_filter(filter_)
      filter_=gtk.FileFilter()
      filter_.set_name("All files")
      filter_.add_pattern("*")
      file_dialog.add_filter(filter_)
      # add to checkboxes if the picture should be created and if it should be .ps
      ps_box=gtk.CheckButton('Picture as Postscript', True)
      ps_box.show()
      pic_box=gtk.CheckButton('Also create Picture', True)
      pic_box.set_active(True)
      pic_box.show()
      file_dialog.vbox.get_children()[-1].pack_start(ps_box, False)
      file_dialog.vbox.get_children()[-1].pack_start(pic_box, False)
      file_dialog.vbox.get_children()[-1].reorder_child(ps_box, 0)
      file_dialog.vbox.get_children()[-1].reorder_child(pic_box, 0)
      response=file_dialog.run()
      if response!=gtk.RESPONSE_OK:
        file_dialog.destroy()
        return None
      self.active_folder=unicode(file_dialog.get_current_folder(), 'utf-8')
      common_folder, common_file_prefix=os.path.split(
              unicode(file_dialog.get_filename().rsplit('.gp', 1)[0], 'utf-8'))
      if ps_box.get_active():
        picture_type='.ps'
      else:
        picture_type='.png'
      file_dialog.destroy()
      if self.active_multiplot:
        multiplot=self.multiplot
        itemlist=[item[0] for item in multiplot]
        plot_text=plotting.create_plotpy(
                                      self.active_session,
                                      itemlist,
                                      common_file_prefix,
                                      '',
                                      multiplot.title,
                                      [item.short_info for item in itemlist],
                                      errorbars,
                                      common_file_prefix+picture_type,
                                      fit_lorentz=False,
                                      sample_name=multiplot.sample_name,
                                      output_file_prefix=common_file_prefix)

        file_numbers=[]
        for j, dataset in enumerate(itemlist):
          for i, attachedset in enumerate(dataset.plot_together):
            file_numbers.append(str(j)+'-'+str(i))
            if getattr(attachedset, 'is_matrix_data', False):
              attachedset.export_matrix(os.path.join(common_folder,
                                  common_file_prefix+str(j)+'-'+str(i)+'.bin'))
            else:
              attachedset.export(os.path.join(common_folder,
                                  common_file_prefix+str(j)+'-'+str(i)+'.out'))
        if itemlist[0].zdata>=0 and plotting.maps_with_projection:
          # export data of projections
          projections_name=os.path.join(common_folder,
                                    common_file_prefix+str(0)+'-'+str(0)+'.xy')
          itemlist[0].export_projections(projections_name)
      else:
        plot_text=plotting.create_plotpy(
                           self.active_session,
                           [self.active_dataset],
                           common_file_prefix,
                           '',
                           self.active_dataset.short_info,
                           [ds.short_info for ds in self.active_dataset.plot_together],
                           errorbars,
                           output_file=common_file_prefix+picture_type,
                           fit_lorentz=False,
                           output_file_prefix=common_file_prefix)
        file_numbers=[]
        j=0
        dataset=self.active_dataset
        for i, attachedset in enumerate(dataset.plot_together):
          file_numbers.append(str(j)+'-'+str(i))
          if  getattr(attachedset, 'is_matrix_data', False):
            attachedset.export_matrix(os.path.join(common_folder, common_file_prefix+str(j)+'-'+str(i)+'.bin'))
          else:
            attachedset.export(os.path.join(common_folder, common_file_prefix+str(j)+'-'+str(i)+'.out'))
        if dataset.zdata>=0 and plotting.maps_with_projection:
          # export data of projections
          projections_name=os.path.join(common_folder, common_file_prefix+str(0)+'-'+str(0)+'.xy')
          dataset.export_projections(projections_name)
      write_file=open(os.path.join(common_folder, common_file_prefix+'.gp'), 'w')
      write_file.write(plot_text+'\n')
      write_file.close()
      if pic_box.get_active():
        subprocess.call([self.active_session.GNUPLOT_COMMAND,
                         common_file_prefix+'.gp'],
                        shell=gnuplot_preferences.EMMULATE_SHELL,
                        creationflags=gnuplot_preferences.PROCESS_FLAGS,
                        stderr=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stdin=subprocess.PIPE,
                        cwd=common_folder
                        )
      #----------------File selection dialog-------------------#      
    elif action.get_name()=='ExportAll':
      if not self.active_multiplot:
        self.export_all()
    elif self.active_multiplot:
      multiplot=self.multiplot
      itemlist=[item[0] for item in multiplot]
      multi_file_name=self.multiplot.sample_name+'_'+self.multiplot.title+'.'+self.set_file_type
      multi_file_name=multi_file_name.replace(' ', '')
      if not action.get_name()=='ExportAs':
        return
      #++++++++++++++++File selection dialog+++++++++++++++++++#
      file_dialog=ExportFileChooserDialog(self.active_session.picture_width,
                                        self.active_session.picture_height,
                                        title='Export multi-plot as...')
      file_dialog.set_default_response(gtk.RESPONSE_OK)
      file_dialog.set_current_name(multi_file_name)
      file_dialog.set_current_folder(self.active_folder)
      # create the filters in the file selection dialog
      filter_=gtk.FileFilter()
      filter_.set_name("Images (png/ps)")
      filter_.add_mime_type("image/png")
      filter_.add_mime_type("image/ps")
      filter_.add_pattern("*.png")
      filter_.add_pattern("*.ps")
      file_dialog.add_filter(filter_)
      filter_=gtk.FileFilter()
      filter_.set_name("All files")
      filter_.add_pattern("*")
      file_dialog.add_filter(filter_)
      response=file_dialog.run()
      if response==gtk.RESPONSE_OK:
        self.active_folder=file_dialog.get_current_folder()
        self.active_session.picture_width, self.active_session.picture_height=file_dialog.get_with_height()
        multi_file_name=unicode(file_dialog.get_filename(), 'utf-8')
      file_dialog.destroy()
      if response!=gtk.RESPONSE_OK:
        return
      #----------------File selection dialog-------------------#

      self.last_plot_text=self.plot(self.active_session,
                                    itemlist,
                                    multiplot[0][1],
                                    multiplot.title,
                                    [item.short_info for item in itemlist],
                                    errorbars,
                                    multi_file_name,
                                    fit_lorentz=False,
                                    sample_name=multiplot.sample_name)
      # give user information in Statusbar
      self.reset_statusbar()
      print 'Export multi-plot '+multi_file_name+'... Done!'
    else:
      new_name=gnuplot_preferences.output_file_name
      if action.get_name()=='ExportAs':
        #++++++++++++++++File selection dialog+++++++++++++++++++#
        file_dialog=ExportFileChooserDialog(self.active_session.picture_width,
                                            self.active_session.picture_height,
                                            title='Export plot as...')
        file_dialog.set_default_response(gtk.RESPONSE_OK)
        file_dialog.set_current_name(os.path.split(
                      self.input_file_name+'_'+self.active_dataset.number+'.'+self.set_file_type)[1])
        file_dialog.set_current_folder(self.active_folder)
        filter_=gtk.FileFilter()
        filter_.set_name("Images (png/ps)")
        filter_.add_mime_type("image/png")
        filter_.add_mime_type("image/ps")
        filter_.add_pattern("*.png")
        filter_.add_pattern("*.ps")
        file_dialog.add_filter(filter_)
        filter_=gtk.FileFilter()
        filter_.set_name("All files")
        filter_.add_pattern("*")
        file_dialog.add_filter(filter_)
        # get hbox widget for the entries
        file_dialog.show_all()
        response=file_dialog.run()
        if response==gtk.RESPONSE_OK:
          self.active_folder=unicode(file_dialog.get_current_folder(), 'utf-8')
          self.active_session.picture_width, self.active_session.picture_height=file_dialog.get_with_height()
          new_name=unicode(file_dialog.get_filename(), 'utf-8')
        elif response==gtk.RESPONSE_CANCEL:
          file_dialog.destroy()
          return False
        file_dialog.destroy()
        #----------------File selection dialog-------------------#
      self.last_plot_text=self.plot(self.active_session,
                                    [self.active_dataset],
                                    self.input_file_name,
                                    self.active_dataset.short_info,
                                    [ds.short_info for ds in self.active_dataset.plot_together],
                                    errorbars,
                                    new_name,
                                    fit_lorentz=False)
      self.reset_statusbar()
      print 'Export plot number '+self.active_dataset.number+'... Done!'

  def export_all(self):
    '''
      Open a Dialog to select which Plots to export with additional options.
    '''
    # Dialog to select the destination folder
    #++++++++++++++++File selection dialog+++++++++++++++++++#
    errorbars=main_window_plotting.errorbars
    file_dialog=ExportFileChooserDialog(self.active_session.picture_width,
                                        self.active_session.picture_height,
                                        title='Select Destination Folder...',
                                        action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                                        buttons=(gtk.STOCK_OK,
                                                 gtk.RESPONSE_OK,
                                                 gtk.STOCK_CANCEL,
                                                 gtk.RESPONSE_CANCEL
                                                 ))
    file_dialog.set_default_response(gtk.RESPONSE_OK)
    file_dialog.set_current_folder(self.active_folder)
    file_dialog.show_all()
    response=file_dialog.run()
    if response==gtk.RESPONSE_OK:
      self.active_folder=unicode(file_dialog.get_current_folder(), 'utf-8')
      self.active_session.picture_width, self.active_session.picture_height=file_dialog.get_with_height()
    else:
      file_dialog.destroy()
      return
    file_dialog.destroy()
    #----------------File selection dialog-------------------#
    # Dialog to select which plots to export
    selection_dialog=PreviewDialog(self.active_session.file_data,
                                   buttons=('Export', 1, 'Cancel', 0))
    selection_dialog.set_default_size(800, 600)
    table=gtk.Table(2, 1, False)
    naming_entry=gtk.Entry()
    naming_entry.set_text('[name]_[nr].png')
    naming_entry.set_width_chars(20)
    naming_entry.connect('activate', lambda*ignore: selection_dialog.response(1))
    table.attach(naming_entry,
              # X direction #          # Y direction
              0, 1, 0, 1,
              0, 0,
              0, 0)
    description=gtk.Label("""      [name] \t- Name of the import file
      [sample]\t- left entry above the plot
      [title_add]\t- right entry above the plot
      [nr]\t\t- Number of the plot""")
    table.attach(description,
              # X direction #          # Y direction
              1, 2, 0, 1,
              0, 0,
              0, 0)
    table.show_all()
    selection_dialog.vbox.pack_end(table, False)
    selection_dialog.set_preview_parameters(self.plot, self.active_session,
                                            self.active_session.TEMP_DIR+'plot_temp.png')
    if selection_dialog.run()==1:
      selection_dialog.hide()
      naming_text=naming_entry.get_text()
      for i, item in enumerate(selection_dialog.get_active_objects_with_key()):
        file_name, dataset=item
        file_name_raw=os.path.split(file_name)[1]
        naming=naming_text.replace('[name]', file_name_raw)
        self.last_plot_text=self.plot(self.active_session,
                                      dataset.plot_together,
                                      file_name,
                                      dataset.short_info,
                                      [ds.short_info for ds in dataset.plot_together],
                                      errorbars,
                                      os.path.join(self.active_folder, naming),
                                      fit_lorentz=False)
        self.reset_statusbar()
        print 'Export plot number %2i...'%i
      print 'Export Done!'
    selection_dialog.destroy()

  def new_ascii_import_filter(self, file_name):
    '''
      Import one or more new datafiles of the same type.
      
      :return: List of names that have been imported.
    '''
    wiz=ImportWizard(file_name)
    result=wiz.run()
    if result!=1:
      wiz.destroy()
      return None
    import_filter=wiz.import_filter
    wiz.destroy()
    return import_filter

  def change_ascii_import_filter(self, action):
    '''
      
    '''

  def read_config_file(self):
    '''
      Read the options that have been stored in a config file in an earlier session.
      The ConfigObj python module is used to save the settings in an .ini file
      as this is an easy way to store dictionaries.
      
      :return: If the import was successful.
    '''
    # create the object with association to an inifile in the user folder
    # have to test if this works under windows
    try:
      self.config_object=ConfigObj(os.path.expanduser('~')+'/.plotpy/config.ini', unrepr=True)
    except:
      # If the file is corrupted or with old format (without unrepr) rename it and create a new one
      print 'Corrupted .ini file, renaming it to config.bak.'
      os.rename(os.path.expanduser('~')+'/.plotpy/config.ini', os.path.expanduser('~')+'/.plotpy/config.bak')
      self.config_object=ConfigObj(os.path.expanduser('~')+'/.plotpy/config.ini', unrepr=True)
    self.config_object.indent_type='\t'
    # If the inifile exists import the profiles but override default profile.
    try:
      self.profiles={'default': PlotProfile('default')}
      self.profiles['default'].save(self)
      for name in self.config_object['profiles'].items():
        self.profiles[name[0]]=PlotProfile(name[0])
        self.profiles[name[0]].read(self.config_object['profiles'])
    except KeyError:
      # create a new object if the file did not exist.
      self.config_object['profiles']={}
      self.profiles={'default': PlotProfile('default')}
      self.profiles['default'].save(self)
    if not 'plot_tree' in self.config_object:
      self.config_object['plot_tree']={
                                       'shown': True,
                                       'size': (350, 500),
                                       'position': (0, 0),
                                       }
    return True

  def read_window_config(self):
    '''
      Read the window config parameters from the ConfigObj.
    '''
    try:
      x, y=self.config_object['Window']['position']
      width, height=self.config_object['Window']['size']
      # Set the main window size to default or the last settings saved in config file
      self.set_default_size(width, height)
      self.move(x, y)
      if 'MouseMode' in self.config_object:
        self.mouse_mode=self.config_object['MouseMode']['active']
    except KeyError:
      self.set_default_size(700, 600)
      # ConfigObj Window parameters
      self.config_object['Window']={
                                    'size': (700, 600),
                                    'position': self.get_position(),
                                    }

