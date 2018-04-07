#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# TRX Toolkit
# Auxiliary tool to generate and send random bursts via TRX DATA
# interface, which may be useful for fuzzing and testing
#
# (C) 2017-2018 by Vadim Yanitskiy <axilirator@gmail.com>
#
# All Rights Reserved
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from copyright import print_copyright
CR_HOLDERS = [("2017-2018", "Vadim Yanitskiy <axilirator@gmail.com>")]

import signal
import getopt
import sys

from rand_burst_gen import RandBurstGen
from data_dump import DATADumpFile
from data_if import DATAInterface
from gsm_shared import *
from data_msg import *

class Application:
	# Application variables
	remote_addr = "127.0.0.1"
	bind_addr = "0.0.0.0"
	base_port = 5700
	conn_mode = "TRX"
	output_file = None

	burst_type = None
	burst_count = 1

	# Common header fields
	fn = None
	tn = None

	# Message specific header fields
	toa256 = None
	rssi = None
	pwr = None

	def __init__(self):
		print_copyright(CR_HOLDERS)
		self.parse_argv()
		self.check_argv()

		# Set up signal handlers
		signal.signal(signal.SIGINT, self.sig_handler)

		# Open requested capture file
		if self.output_file is not None:
			self.ddf = DATADumpFile(self.output_file)

	def run(self):
		# Init DATA interface with TRX or L1
		if self.conn_mode == "TRX":
			self.data_if = DATAInterface(self.remote_addr, self.base_port + 2,
				self.bind_addr, self.base_port + 102)
		elif self.conn_mode == "L1":
			self.data_if = DATAInterface(self.remote_addr, self.base_port + 102,
				self.bind_addr, self.base_port + 2)

		# Init random burst generator
		burst_gen = RandBurstGen()

		# Init an empty DATA message
		if self.conn_mode == "TRX":
			msg = DATAMSG_L12TRX()
		elif self.conn_mode == "L1":
			msg = DATAMSG_TRX2L1()

		# Generate a random frame number or use provided one
		fn_init = msg.rand_fn() if self.fn is None else self.fn

		# Send as much bursts as required
		for i in range(self.burst_count):
			# Randomize the message header
			msg.rand_hdr()

			# Increase and set frame number
			msg.fn = (fn_init + i) % GSM_HYPERFRAME

			# Set timeslot number
			if self.tn is not None:
				msg.tn = self.tn

			# Set transmit power level
			if self.pwr is not None:
				msg.pwr = self.pwr

			# Set time of arrival
			if self.toa256 is not None:
				msg.toa256 = self.toa256

			# Set RSSI
			if self.rssi is not None:
				msg.rssi = self.rssi

			# Generate a random burst
			if self.burst_type == "NB":
				burst = burst_gen.gen_nb()
			elif self.burst_type == "FB":
				burst = burst_gen.gen_fb()
			elif self.burst_type == "SB":
				burst = burst_gen.gen_sb()
			elif self.burst_type == "AB":
				burst = burst_gen.gen_ab()

			# Convert to soft-bits in case of TRX -> L1 message
			if self.conn_mode == "L1":
				burst = msg.ubit2sbit(burst)

			# Set burst
			msg.burst = burst

			print("[i] Sending %d/%d %s burst %s to %s..."
				% (i + 1, self.burst_count, self.burst_type,
					msg.desc_hdr(), self.conn_mode))

			# Send message
			self.data_if.send_msg(msg)

			# Append a new message to the capture
			if self.output_file is not None:
				self.ddf.append_msg(msg)

	def print_help(self, msg = None):
		s  = " Usage: " + sys.argv[0] + " [options]\n\n" \
			 " Some help...\n" \
			 "  -h --help           this text\n\n"

		s += " TRX interface specific\n" \
			 "  -o --output-file    Write bursts to a capture file\n"        \
			 "  -m --conn-mode      Send bursts to: TRX (default) / L1\n"    \
			 "  -r --remote-addr    Set remote address (default %s)\n"       \
			 "  -b --bind-addr      Set local address (default %s)\n"        \
			 "  -p --base-port      Set base port number (default %d)\n\n"

		s += " Burst generation\n" \
			 "  -b --burst-type     Random burst type (NB, FB, SB, AB)\n"    \
			 "  -c --burst-count    How much bursts to send (default 1)\n"   \
			 "  -f --frame-number   Set frame number (default random)\n"     \
			 "  -t --timeslot       Set timeslot index (default random)\n"   \
			 "     --pwr            Set power level (default random)\n"      \
			 "     --rssi           Set RSSI (default random)\n"             \
			 "     --toa            Set ToA in symbols (default random)\n"   \
			 "     --toa256         Set ToA in 1/256 symbol periods\n"

		print(s % (self.remote_addr, self.bind_addr, self.base_port))

		if msg is not None:
			print(msg)

	def parse_argv(self):
		try:
			opts, args = getopt.getopt(sys.argv[1:],
				"o:m:r:b:p:b:c:f:t:h",
				[
					"help",
					"output-file="
					"conn-mode=",
					"remote-addr=",
					"bind-addr=",
					"base-port=",
					"burst-type=",
					"burst-count=",
					"frame-number=",
					"timeslot=",
					"rssi=",
					"toa=",
					"toa256=",
					"pwr=",
				])
		except getopt.GetoptError as err:
			self.print_help("[!] " + str(err))
			sys.exit(2)

		for o, v in opts:
			if o in ("-h", "--help"):
				self.print_help()
				sys.exit(2)

			elif o in ("-o", "--output-file"):
				self.output_file = v
			elif o in ("-m", "--conn-mode"):
				self.conn_mode = v
			elif o in ("-r", "--remote-addr"):
				self.remote_addr = v
			elif o in ("-b", "--bind-addr"):
				self.bind_addr = v
			elif o in ("-p", "--base-port"):
				self.base_port = int(v)

			elif o in ("-b", "--burst-type"):
				self.burst_type = v
			elif o in ("-c", "--burst-count"):
				self.burst_count = int(v)
			elif o in ("-f", "--frame-number"):
				self.fn = int(v)
			elif o in ("-t", "--timeslot"):
				self.tn = int(v)

			# Message specific header fields
			elif o == "--pwr":
				self.pwr = int(v)
			elif o == "--rssi":
				self.rssi = int(v)
			elif o == "--toa256":
				self.toa256 = int(v)
			elif o == "--toa":
				self.toa256 = int(float(v) * 256.0 + 0.5)

	def check_argv(self):
		# Check connection mode
		if self.conn_mode not in ("TRX", "L1"):
			self.print_help("[!] Unknown connection type")
			sys.exit(2)

		# Check connection mode
		if self.burst_type not in ("NB", "FB", "SB", "AB"):
			self.print_help("[!] Unknown burst type")
			sys.exit(2)

	def sig_handler(self, signum, frame):
		print("Signal %d received" % signum)
		if signum is signal.SIGINT:
			sys.exit(0)

if __name__ == '__main__':
	app = Application()
	app.run()
