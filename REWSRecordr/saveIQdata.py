#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: IQdataSave
# Author: Measurements
# Description: This app records data using USRP with Gnuradio-companion
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
from datetime import datetime
from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import uhd
import time
import os
import sip
import threading

from PyQt5.QtWidgets import QDialog, QMessageBox, QFileDialog
from ipVal import IPInputDialog

class saveIQdata(gr.top_block, Qt.QWidget):

    def __init__(self, usrp_ip="192.168.1py0.2"):
        gr.top_block.__init__(self, "IQdataSave", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("IQdataSave")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except BaseException as exc:
            print(f"Qt GUI: Could not set Icon: {str(exc)}", file=sys.stderr)
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "saveIQdata")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 5e6
        self.rootdir = rootdir = str(os.path.expanduser("~")+"/")
        self.note = note = 'RECORDING_NOTE'
        self.gain = gain = 0
        self.freq = freq = 5e6
        self.rec_button = rec_button = 0
        self.filename = filename = rootdir+note+"_"+str(int(freq))+"Hz_"+str(int(samp_rate))+"sps_"+str(int(gain))+"db_"
        self.file_path_btn = file_path_btn = '0'
        self.amp = amp = 0.01

        self.max_bytes = 500 * 1024 * 1024  # 500MB

        self.bytes_written = 0
        self.file_counter = 0
        self.current_file = None

        # Start a timer that checks file size every second
        self.file_monitor_timer = QtCore.QTimer()
        self.file_monitor_timer.timeout.connect(self.check_file_size)
        self.file_monitor_timer.start(1000)  # every 1 second

        self.recording_dir = None

        ##################################################
        # Blocks
        ##################################################

        self._rec_button_push_button = Qt.QPushButton('RECORD')

        self._rec_button_choices = {'Pressed': 1, 'Released': 0}
        self._rec_button_push_button.clicked.connect(self.toggle_recording)
        self.top_grid_layout.addWidget(self._rec_button_push_button, 0, 3, 1, 1)

        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(3, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._gain_range = qtgui.Range(0, 93, 1, 0, 200)
        self._gain_win = qtgui.RangeWidget(self._gain_range, self.set_gain, "RX Gain", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._gain_win, 1, 0, 1, 4)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._freq_range = qtgui.Range(10, 500e6, 1e3, 5e6, 200)
        self._freq_win = qtgui.RangeWidget(self._freq_range, self.set_freq, "Frequency", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._freq_win, 2, 0, 1, 4)
        for r in range(2, 3):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._amp_range = qtgui.Range(0.005, 10, .005, 0.01, 200)
        self._amp_win = qtgui.RangeWidget(self._amp_range, self.set_amp, "Amplitude", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._amp_win, 5, 0, 1, 4)
        for r in range(5, 6):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        try:
            self.uhd_usrp_source_0 = uhd.usrp_source(
                ",".join((f"addr={usrp_ip}", '')),
                uhd.stream_args(
                    cpu_format="fc32",
                    args='',
                    channels=list(range(0,1)),
                ),
            )
        except:
            QMessageBox.critical(self, "Error: Invalid IP Address" , "No device found at that IP address "+ str(usrp_ip))

        self.uhd_usrp_source_0.set_samp_rate(samp_rate)
        self.uhd_usrp_source_0.set_time_unknown_pps(uhd.time_spec(0))

        self.uhd_usrp_source_0.set_center_freq(freq, 0)
        self.uhd_usrp_source_0.set_antenna("RX1", 0)
        self.uhd_usrp_source_0.set_gain(gain, 0)
        self.qtgui_waterfall_sink_x_0 = qtgui.waterfall_sink_c(
            1024, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            freq, #fc
            samp_rate, #bw
            "", #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_waterfall_sink_x_0.set_update_time(0.10)
        self.qtgui_waterfall_sink_x_0.enable_grid(False)
        self.qtgui_waterfall_sink_x_0.enable_axis_labels(True)



        labels = ['', '', '', '', '',
                  '', '', '', '', '']
        colors = [0, 0, 0, 0, 0,
                  0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
                  1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_waterfall_sink_x_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_waterfall_sink_x_0.set_line_label(i, labels[i])
            self.qtgui_waterfall_sink_x_0.set_color_map(i, colors[i])
            self.qtgui_waterfall_sink_x_0.set_line_alpha(i, alphas[i])

        self.qtgui_waterfall_sink_x_0.set_intensity_range(-140, 10)

        self._qtgui_waterfall_sink_x_0_win = sip.wrapinstance(self.qtgui_waterfall_sink_x_0.qwidget(), Qt.QWidget)

        self.top_grid_layout.addWidget(self._qtgui_waterfall_sink_x_0_win, 8, 0, 1, 4)
        for r in range(8, 9):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.qtgui_time_sink_x_0 = qtgui.time_sink_c(
            4096, #size
            samp_rate, #samp_rate
            "", #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_time_sink_x_0.set_update_time(0.10)
        self.qtgui_time_sink_x_0.set_y_axis(-(amp), amp)

        self.qtgui_time_sink_x_0.set_y_label('Amplitude', "")

        self.qtgui_time_sink_x_0.enable_tags(True)
        self.qtgui_time_sink_x_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.qtgui_time_sink_x_0.enable_autoscale(False)
        self.qtgui_time_sink_x_0.enable_grid(False)
        self.qtgui_time_sink_x_0.enable_axis_labels(True)
        self.qtgui_time_sink_x_0.enable_control_panel(False)
        self.qtgui_time_sink_x_0.enable_stem_plot(False)


        labels = ['Signal 1', 'Signal 2', 'Signal 3', 'Signal 4', 'Signal 5',
            'Signal 6', 'Signal 7', 'Signal 8', 'Signal 9', 'Signal 10']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'red', 'green', 'black', 'cyan',
            'magenta', 'yellow', 'dark red', 'dark green', 'dark blue']
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(2):
            if len(labels[i]) == 0:
                if (i % 2 == 0):
                    self.qtgui_time_sink_x_0.set_line_label(i, "Re{{Data {0}}}".format(i/2))
                else:
                    self.qtgui_time_sink_x_0.set_line_label(i, "Im{{Data {0}}}".format(i/2))
            else:
                self.qtgui_time_sink_x_0.set_line_label(i, labels[i])
            self.qtgui_time_sink_x_0.set_line_width(i, widths[i])
            self.qtgui_time_sink_x_0.set_line_color(i, colors[i])
            self.qtgui_time_sink_x_0.set_line_style(i, styles[i])
            self.qtgui_time_sink_x_0.set_line_marker(i, markers[i])
            self.qtgui_time_sink_x_0.set_line_alpha(i, alphas[i])

        self._qtgui_time_sink_x_0_win = sip.wrapinstance(self.qtgui_time_sink_x_0.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._qtgui_time_sink_x_0_win, 6, 0, 2, 4)
        for r in range(6, 8):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.qtgui_freq_sink_x_0 = qtgui.freq_sink_c(
            1024, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            freq, #fc
            samp_rate, #bw
            "", #name
            1,
            None # parent
        )
        self.qtgui_freq_sink_x_0.set_update_time(0.10)
        self.qtgui_freq_sink_x_0.set_y_axis((-140), 10)
        self.qtgui_freq_sink_x_0.set_y_label('Relative Gain', 'dB')
        self.qtgui_freq_sink_x_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.qtgui_freq_sink_x_0.enable_autoscale(False)
        self.qtgui_freq_sink_x_0.enable_grid(False)
        self.qtgui_freq_sink_x_0.set_fft_average(1.0)
        self.qtgui_freq_sink_x_0.enable_axis_labels(True)
        self.qtgui_freq_sink_x_0.enable_control_panel(False)
        self.qtgui_freq_sink_x_0.set_fft_window_normalized(False)



        labels = ['', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_freq_sink_x_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_freq_sink_x_0.set_line_label(i, labels[i])
            self.qtgui_freq_sink_x_0.set_line_width(i, widths[i])
            self.qtgui_freq_sink_x_0.set_line_color(i, colors[i])
            self.qtgui_freq_sink_x_0.set_line_alpha(i, alphas[i])

        self._qtgui_freq_sink_x_0_win = sip.wrapinstance(self.qtgui_freq_sink_x_0.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._qtgui_freq_sink_x_0_win, 3, 0, 2, 4)
        for r in range(3, 5):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._note_tool_bar = Qt.QToolBar(self)
        self._note_tool_bar.addWidget(Qt.QLabel("RECORDING NOTE (press enter to update)" + ": "))
        self._note_line_edit = Qt.QLineEdit(str(self.note))
        self._note_tool_bar.addWidget(self._note_line_edit)
        self._note_line_edit.editingFinished.connect(
            lambda: self.set_note(str(str(self._note_line_edit.text()))))
        self.top_grid_layout.addWidget(self._note_tool_bar, 0, 1, 1, 2)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(1, 3):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._file_path_btn_push_button = Qt.QPushButton(rootdir)
        self._file_path_btn_push_button = Qt.QPushButton(rootdir)
        self._file_path_btn_choices = {'Pressed': '1', 'Released': '0'}
        self._file_path_btn_push_button.pressed.connect(self.getDirectory)
        self.top_grid_layout.addWidget(self._file_path_btn_push_button, 0, 0, 1, 1)

        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.blocks_file_sink_0 = blocks.file_sink(gr.sizeof_gr_complex*1, filename+str(datetime.fromtimestamp(time.time()).strftime('%Y_%m_%d_%H_%M_%S'))+".dat" if rec_button == 1 else "/dev/null", False)
        self.blocks_file_sink_0.set_unbuffered(False)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.uhd_usrp_source_0, 0), (self.blocks_file_sink_0, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.qtgui_freq_sink_x_0, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.qtgui_time_sink_x_0, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.qtgui_waterfall_sink_x_0, 0))

    def set_controls_enabled(self, enabled):
        self._gain_win.setEnabled(enabled)
        self._freq_win.setEnabled(enabled)
        self._amp_win.setEnabled(enabled)
        self._note_line_edit.setEnabled(enabled)
        self._file_path_btn_push_button.setEnabled(enabled)


    def toggle_recording(self):
        if self.rec_button == 0:
            # Start recording
            self.set_rec_button(1)
            self._rec_button_push_button.setText("STOP")
            self.set_controls_enabled(False)
        else:
            # Stop recording
            self.set_rec_button(0)
            self._rec_button_push_button.setText("RECORD")
            self.set_controls_enabled(True)


    def generate_filename(self):
        timestamp = datetime.fromtimestamp(time.time()).strftime('%Y_%m_%d_%H_%M_%S')
        base = f"{self.note}_{int(self.freq)}Hz_{int(self.samp_rate)}sps_{int(self.gain)}db"
        filename = f"{base}_{timestamp}_part{self.file_counter}.dat"
        return os.path.join(self.recording_dir, filename) if self.recording_dir else "/dev/null"
    
    def check_file_size(self):
        if self.rec_button != 1 or not self.current_file:
            return

        try:
            self.bytes_written = os.path.getsize(self.current_file)
            if self.bytes_written >= self.max_bytes:
                self.file_counter += 1
                filename = self.generate_filename()
                self.blocks_file_sink_0.open(filename)
                self.current_file = filename
                self.bytes_written = 0
                print(f"📂 Switched to new file: {filename}")
        except Exception as e:
            print(f"File size check error: {e}")


    def getDirectory(self):
        response = QFileDialog.getExistingDirectory(
            self,
            caption='Select a folder'
        )
        #print(response)
        
        self.set_rootdir(response + "/")
        self._file_path_btn_push_button.setText(response +"/")
        #print(self.get_rootdir())

    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "saveIQdata")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.set_filename(self.rootdir+self.note+"_"+str(int(self.freq))+"Hz_"+str(int(self.samp_rate))+"sps_"+str(int(self.gain))+"db_")
        self.qtgui_freq_sink_x_0.set_frequency_range(self.freq, self.samp_rate)
        self.qtgui_time_sink_x_0.set_samp_rate(self.samp_rate)
        self.qtgui_waterfall_sink_x_0.set_frequency_range(self.freq, self.samp_rate)
        self.uhd_usrp_source_0.set_samp_rate(self.samp_rate)

    def get_rootdir(self):
        return self.rootdir

    def set_rootdir(self, rootdir):
        self.rootdir = rootdir
        self.set_filename(self.rootdir+self.note+"_"+str(int(self.freq))+"Hz_"+str(int(self.samp_rate))+"sps_"+str(int(self.gain))+"db_")

    def get_note(self):
        return self.note

    def set_note(self, note):
        self.note = note
        self.set_filename(self.rootdir+self.note+"_"+str(int(self.freq))+"Hz_"+str(int(self.samp_rate))+"sps_"+str(int(self.gain))+"db_")
        Qt.QMetaObject.invokeMethod(self._note_line_edit, "setText", Qt.Q_ARG("QString", str(self.note)))

    def get_gain(self):
        return self.gain

    def set_gain(self, gain):
        self.gain = gain
        self.set_filename(self.rootdir+self.note+"_"+str(int(self.freq))+"Hz_"+str(int(self.samp_rate))+"sps_"+str(int(self.gain))+"db_")
        self.uhd_usrp_source_0.set_gain(self.gain, 0)

    def get_freq(self):
        return self.freq

    def set_freq(self, freq):
        self.freq = freq
        self.set_filename(self.rootdir+self.note+"_"+str(int(self.freq))+"Hz_"+str(int(self.samp_rate))+"sps_"+str(int(self.gain))+"db_")
        self.qtgui_freq_sink_x_0.set_frequency_range(self.freq, self.samp_rate)
        self.qtgui_waterfall_sink_x_0.set_frequency_range(self.freq, self.samp_rate)
        self.uhd_usrp_source_0.set_center_freq(self.freq, 0)

    def get_rec_button(self):
        return self.rec_button

    def set_rec_button(self, rec_button):
        self.rec_button = rec_button
        if self.rec_button == 1:
            timestamp = datetime.fromtimestamp(time.time()).strftime('%Y_%m_%d_%H_%M_%S')
            self.recording_dir = os.path.join(self.rootdir, f"{self.note}_{timestamp}")
            os.makedirs(self.recording_dir, exist_ok=True)

            self.file_counter = 1
            self.bytes_written = 0
            filename = self.generate_filename()
            self.blocks_file_sink_0.open(filename)
            self.current_file = filename
            print(f"📁 Recording started in: {self.recording_dir}")
        else:
            self.blocks_file_sink_0.open("/dev/null")
            self.current_file = None
            self.recording_dir = None

    def get_filename(self):
        return self.filename

    def set_filename(self, filename):
        self.filename = filename
        self.blocks_file_sink_0.open(self.filename+str(datetime.fromtimestamp(time.time()).strftime('%Y_%m_%d_%H_%M_%S'))+".dat" if self.rec_button == 1 else "/dev/null")

    def get_file_path_btn(self):
        return self.file_path_btn

    def set_file_path_btn(self, file_path_btn):
        self.file_path_btn = file_path_btn

    def get_amp(self):
        return self.amp

    def set_amp(self, amp):
        self.amp = amp
        self.qtgui_time_sink_x_0.set_y_axis(-(self.amp), self.amp)




def main(top_block_cls=saveIQdata, options=None):
    qapp = Qt.QApplication(sys.argv)

    # Show IP input dialog
    dialog = IPInputDialog()
    if dialog.exec_() != QDialog.Accepted:
        sys.exit(0)

    ip_address = dialog.get_ip()
    print(f"Using IP address: {ip_address}")

    tb = top_block_cls(ip_address)
    tb.start()
    tb.flowgraph_started.set()
    tb.show()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()
        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    qapp.exec_()

if __name__ == '__main__':
    main()
