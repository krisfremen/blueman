# Copyright (C) 2008 Valmantas Paliksa <walmis at balticum-tv dot lt>
# Copyright (C) 2008 Tadas Dailyda <tadas at dailyda dot com>
#
# Licensed under the GNU General Public License Version 3
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# 
from blueman.Functions import *
from blueman.plugins.AppletPlugin import AppletPlugin
import blueman.bluez as Bluez
from blueman.bluez.errors import BluezDBusException
import dbus
import types

class PowerManager(AppletPlugin):
	__depends__ = ["StatusIcon", "Menu"]
	__unloadable__ = False
	__description__ = _("Controls bluetooth adapter power states")
	__author__ = "Walmis"
	
	def on_load(self, applet):
		AppletPlugin.add_method(self.on_power_state_query)
		AppletPlugin.add_method(self.on_power_state_change_requested)
		AppletPlugin.add_method(self.on_power_state_changed)
		
		self.Applet = applet
		
		self.item = create_menuitem(_("<b>Bluetooth Off</b>"), get_icon("gtk-stop", 16))
		self.item.get_child().set_markup(_("<b>Turn Bluetooth Off</b>"))
		
		self.item.props.tooltip_text = _("Turn off all adapters")
		self.item.connect("activate", lambda x: self.on_bluetooth_toggled())
		
		dbus.SystemBus().add_signal_receiver(self.adapter_property_changed, "PropertyChanged", "org.bluez.Adapter", "org.bluez", path_keyword="path")
		
		self.Applet.Plugins.Menu.Register(self, self.item, 0)
		
		self.Applet.DbusSvc.add_method(self.SetBluetoothStatus, in_signature="b", out_signature="")
		self.Applet.DbusSvc.add_method(self.GetBluetoothStatus, in_signature="", out_signature="b")
		self.BluetoothStatusChanged = self.Applet.DbusSvc.add_signal("BluetoothStatusChanged", signature="b")
		
		self.adapter_state = True
		self.current_state = True
		self.power_changeable = True
		
		self.STATE_ON = 2
		self.STATE_OFF = 1
		self.STATE_OFF_FORCED = 0
		
		gobject.idle_add(self.UpdatePowerState)
	
	@property	
	def CurrentState(self):
		return self.current_state
		
	def on_manager_state_changed(self, state):
		if state:
			self.adapter_state = self.get_adapter_state()
			self.RequestPowerState(self.adapter_state)
		
	def get_adapter_state(self):
		adapters = self.Applet.Manager.ListAdapters()
		for adapter in adapters:
			props = adapter.GetProperties()
			if not props["Powered"]:
				return False
		return True
		
	def set_adapter_state(self, state):
		adapters = self.Applet.Manager.ListAdapters()
		for adapter in adapters:
			adapter.SetProperty("Powered", state)
	
		self.adapter_state = state	
		
	def RequestPowerState(self, state):
		if self.current_state != state:
			dprint("Requesting", state)
			self.Applet.Plugins.Run("on_power_state_change_requested", self, state)
			self.set_adapter_state(state)
		
	def on_power_state_change_requested(self, pm, state):
		pass
		
	def on_power_state_query(self, pm):
		if self.adapter_state:
			return self.STATE_ON
		else:
			return self.STATE_OFF
		
	def on_power_state_changed(self, manager, state):
		pass
	
	
	#queries other plugins to determine the current power state
	def UpdatePowerState(self):
		rets = self.Applet.Plugins.Run("on_power_state_query", self)

		off = True in map(lambda x: x < self.STATE_ON, rets)
		foff = self.STATE_OFF_FORCED in rets
		on = self.STATE_ON in rets
		
		
		
		new_state = True
		if foff or off:
				
			self.item.get_child().set_markup(_("<b>Turn Bluetooth On</b>"))
			self.item.props.tooltip_text = _("Turn on all adapters")
			self.item.set_image(gtk.image_new_from_pixbuf(get_icon("gtk-yes", 16)))
			
			if foff:
				self.item.props.sensitive = False
			else:
				self.item.props.sensitive = True
			
			new_state = False
		
		elif on and self.current_state != True:
			self.item.get_child().set_markup(_("<b>Turn Bluetooth Off</b>"))
			self.item.props.tooltip_text = _("Turn off all adapters")
			self.item.set_image(gtk.image_new_from_pixbuf(get_icon("gtk-stop", 16)))
			self.item.props.sensitive = True
			
			new_state = True
			
		dprint("off", off, "\nfoff", foff, "\non", on, "\ncurrent state", self.current_state, "\nnew state", new_state)
	
		if self.current_state != new_state:
			dprint("Signalling", new_state)
			self.current_state = new_state
			
			self.BluetoothStatusChanged(new_state)	
			self.Applet.Plugins.Run("on_power_state_changed", self, new_state)
			self.Applet.Plugins.StatusIcon.IconShouldChange()
		
	#dbus method
	def SetBluetoothStatus(self, status):
		pass
	
	#dbus method
	def GetBluetoothStatus(self):
		return self.CurrentState
		
	def adapter_property_changed(self, key, value, path):
		if key == "Powered":
			if value and not self.CurrentState:
				dprint("adapter powered on while in off state, turning bluetooth on")
				self.RequestPowerState(True)
			
			self.UpdatePowerState()

	
	def on_bluetooth_toggled(self):
		self.RequestPowerState(not self.CurrentState)
		
	def on_status_icon_pixbuf_ready(self, pixbuf):
		opacity = 255 if self.GetBluetoothStatus() else 100
		pixbuf = opacify_pixbuf(pixbuf, opacity)

		if opacity < 255:
			x_size = int(pixbuf.props.height / 2.1)
			x = get_icon("blueman-x", x_size) 
			pixbuf = composite_icon(pixbuf, [(x, pixbuf.props.height - x_size, pixbuf.props.height - x_size, 200)])
		
		return pixbuf
		
#	def process_deferred(self):
#		if self.state_change_deferred != -1:
#			dprint("Setting deferred status")
#			self.bluetooth_off = self.state_change_deferred
#			self.state_change_deferred = -1
		
	def on_adapter_added(self, path):
		adapter = Bluez.Adapter(path)
		def on_ready():
			if not self.adapter_state:
				adapter.SetProperty("Powered", False)
			else:
				adapter.SetProperty("Powered", True)				
		
		wait_for_adapter(adapter, on_ready)
		
	def SetPowerChangeable(self, state):
		self.power_changeable = state
		self.item.props.sensitive = state
	

#	def __setattr__(self, key, value):
#		if key == "bluetooth_off":
#			dprint("bt_off", value)
#			dprint("manager state", self.Applet.Manager)
#				
#			def set_global_state():
#				if key in self.__dict__:
#					dprint("off", self.__dict__[key], value)
#					adapters = self.Applet.Manager.ListAdapters()
#					for adapter in adapters:
#						adapter.SetProperty("Powered", not value)
#		
#			
#			def error(e):
#				d = gtk.MessageDialog(parent=None, flags=0, type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_CLOSE, message_format=None)
#				
#				d.props.text = _("Failed to set bluetooth power")
#				d.props.secondary_text = _("The error reported is: %s") % str(e)
#				d.props.icon_name = "blueman"
#				d.run()
#				d.destroy()
#			
#			if not key in self.__dict__:
#				self.__dict__[key] = value
#			
#			if not self.Applet.Manager:
#				dprint("deferring status change")
#				self.state_change_deferred = value
#				return
#			
#			if self.__dict__[key] != value:
#				self.__dict__[key] = value
#									
#				if value:
#					try:
#						set_global_state()
#					except BluezDBusException, e:	
#						error(e)
#						return
#				

#					
#					#FIXME: possible race condition here
#					try:
#						set_global_state()
#					except BluezDBusException, e:	
#						error(e)
#						self.bluetooth_off = True
#						return
#							
#				self.Applet.Plugins.StatusIcon.IconShouldChange()
#		else:				
#			self.__dict__[key] = value

