"""Basic Package."""

import numpy as np

from .base import MFPackageDIS
from .reader import MFFileReader

__all__ = ["BAS6"]


class BAS6(MFPackageDIS):
    """Basic Package."""

    valid_options = [
        "XSECTION",
        "CHTOCH",
        "FREE",
        "PRINTTIME",
        "SHOWPROGRESS",
        "STOPERROR",
    ]

    _Options = []

    @property
    def Options(self):
        """List of Options."""
        return self._Options

    @Options.setter
    def Options(self, value) -> None:
        self._Options = value

    @property
    def free(self):
        """Indicates that free format is used for input variables throughout
        the Basic Package and other packages as indicated in their input
        instructions.
        """
        w = "FREE"
        return any([k in self.Options for k in [w, w.lower(), w.upper()]])

    @free.setter
    def free(self, value) -> None:
        cur = self.free
        w = "FREE"
        if value and not cur:
            self.Options.append(w)
        elif not value and cur:
            for k in [w, w.lower(), w.upper()]:
                if k in self.Options:
                    self.Options.remove(k)

    @property
    def xsection(self):
        """Indicates that the model is a 1-row cross section for which STRT
        and IBOUND should each be read as single two-dimensional variables
        with dimensions of NCOL and NLAY.
        """
        w = "XSECTION"
        return any([k in self.Options for k in [w, w.lower(), w.upper()]])

    @xsection.setter
    def xsection(self, value) -> None:
        cur = self.free
        w = "XSECTION"
        if value and not cur:
            self.Options.append(w)
        elif not value and cur:
            for k in [w, w.lower(), w.upper()]:
                if k in self.Options:
                    self.Options.remove(k)

    @property
    def Ibound(self):
        """The boundary variable array, which is < 0 for constant heads,
        = 0 for inactive cells and > 0 for active cells.
        """
        return getattr(self, "_Ibound", None)

    @Ibound.setter
    def Ibound(self, value) -> None:
        self._Ibound = value

    @property
    def hnoflo(self):
        """The value of head to be assigned to all inactive (no flow) cells
        (ibound == 0) throughout the simulation.
        """
        return getattr(self, "_hnoflo", None)

    @hnoflo.setter
    def hnoflo(self, value) -> None:
        self._hnoflo = value

    @property
    def Strt(self):
        """Initial or starting head array."""
        return getattr(self, "_Strt", None)

    @Strt.setter
    def Strt(self, value) -> None:
        self._Strt = value

    def read(self, fpath=None) -> None:
        """Read BAS6 file."""
        self._setup_read()
        fp = MFFileReader(fpath, self)
        try:
            # 0: [#Text]
            fp.read_text(0)
            # 1: Options
            fp.read_options(1, False)
            if self.disu:
                # 2a. IBOUND(NDSLAY) -- U1DINT
                self.Ibound = []
                if not self.xsection:
                    for ilay, ndslay in enumerate(self.disu.Nodelay):
                        n = "2a:L" + str(ilay + 1)
                        self.Ibound.append(fp.get_array(n, ndslay, self._float_type))
                else:  # same???
                    for ilay, ndslay in enumerate(self.disu.Nodelay):
                        n = "2a:L" + str(ilay + 1)
                        self.Ibound.append(fp.get_array(n, ndslay, self._float_type))
            elif self.xsection:
                assert self.dis.nrow == 1, self.dis.nrow
                LC_shape = (self.dis.nlay, self.dis.ncol)
                self.Ibound = fp.get_array("2b", LC_shape, "i")
            else:
                self.Ibound = np.empty(self.dis.shape3d, "i")
                for ilay in range(self.dis.nlay):
                    n = "2b:L" + str(ilay + 1)
                    self.Ibound[ilay, :, :] = fp.get_array(n, self.dis.shape2d, "i")
            # 3: HNOFLO (10-character field unless Item 1 contains 'FREE'.)
            line = fp.next_line(3)
            if self.free:
                self.hnoflo = self._float_type.type(line.split()[0])
            else:
                self.hnoflo = self._float_type.type(line[0:10])
            # 4: STRT(NCOL,NROW) or (NCOL,NLAY) -- U2DREL
            if self.xsection:
                self.strt = fp.get_array(4, LC_shape, self._float_type)
            else:
                self.strt = np.empty(self.dis.shape3d, self._float_type)
                for ilay in range(self.dis.nlay):
                    self.strt[ilay, :, :] = fp.get_array(
                        4, self.dis.shape2d, self._float_type,
                    )
            fp.check_end()
        except Exception as e:
            exec(fp.location_exception(e))
