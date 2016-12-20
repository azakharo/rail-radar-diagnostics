#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import Cfg
from windows_networking import parseIpconfigOutput


class TestGettingEthernetInfo(unittest.TestCase):

    def testEthExists(self):
        f = open('ethExists.txt')
        cont = f.read()
        f.close()
        eth = parseIpconfigOutput(cont)
        self.assertIsNotNone(eth)
        self.assertEqual(eth.ifaceName, u'Ethernet')
        self.assertTrue(eth.isConnected)
        self.assertEqual(eth.ip, u'10.10.2.97')

    def testEthDoesntExist(self):
        f = open('ethDoesntExist.txt')
        cont = f.read()
        f.close()
        eth = parseIpconfigOutput(cont)
        self.assertIsNotNone(eth)
        self.assertEqual(eth.ifaceName, u'Ethernet')
        self.assertFalse(eth.isConnected)
        self.assertIsNone(eth.ip)


if __name__ == '__main__':
    unittest.main()
