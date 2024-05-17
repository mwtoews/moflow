from typing import NoReturn

import numpy as np

from .base import _MFPackageDIS
from .reader import MFFileReader


class RCH(_MFPackageDIS):
    """Recharge Package."""

    @property
    def nrchop(self):
        """Recharge option code of either 1, 2 or 3.
        * 1: Recharge is only to the top grid layer.
        * 2: Vertical distribution of recharge is specified in layer
             variable IRCH.
        * 3: Recharge is applied to the highest active cell in each
             vertical column. A constant-head node intercepts recharge and
             prevents deeper infiltration.
        """
        return getattr(self, "_nrchop", None)

    @nrchop.setter
    def nrchop(self, value) -> None:
        if value not in (None, 1, 2, 3):
            raise ValueError("invalid 'nrchop: must be 1, 2, or 3")
        self._nrchop = value

    @property
    def irchcb(self):
        """Flag and a unit number for writing cell-by-cell flow terms."""
        return getattr(self, "_irchcb", None)

    @irchcb.setter
    def irchcb(self, value) -> None:
        self._irchcb = value

    @property
    def Rech(self):
        """Recharge flux array with dimensions (nper, nrow, ncol)."""
        return getattr(self, "_Rech", None)

    @Rech.setter
    def Rech(self, value) -> None:
        self._Rech = value

    @property
    def Irch(self):
        """Layer number variable that defines the layer in each vertical
        column where recharge is applied.
        """
        return getattr(self, "_Irch", None)

    @Irch.setter
    def Irch(self, value) -> None:
        if value is not None and self.nrchop != 2:
            self._logger.error("'nrchop' must be 2")
        self._Irch = value

    def read(self, fpath=None) -> NoReturn:
        """Read RCH file."""
        raise NotImplementedError
        self._setup_read()
        fp = MFFileReader(fpath, self)
        try:
            # 0: [#Text]
            fp.read_text(0)
            # 1: [ PARAMETER NPRCH]
            fp.read_parameter(1, ["nprch"])
            # 2: NRCHOP IRCHCB
            fp.read_named_items(2, ["nrchop", "irchcb"], fmt="i")
            if self.disu:
                # 2b. MXNDRCH
                fp.read_named_items(2, ["mxndrch"], fmt="i")
            # Repeat Items 3 and 4 for each parameter; NPRCH times
            for ipar in range(self.nprch):
                # 3: [PARNAM PARTYP Parval NCLU [INSTANCES NUMINST]]
                # 4a: [INSTNAM]
                # 4b: [Mltarr Zonarr IZ]
                raise NotImplementedError("PARAMETER not suported")
            if self.dis:
                top_shape = (self.dis.nper, self.dis.nrow, self.dis.ncol)
                shape2d = self.dis.shape2d
                self.Rech = np.empty(top_shape, self._float_type)
                if self.nrchop == 2:
                    self.Irch = np.empty(top_shape, "i")
                else:
                    self.Irch = None

            # FOR EACH STRESS PERIOD
            stress_period = 0
            for sp in range(self.nper):
                stress_period += 1
                # 5: INRECH [INIRCH]
                if self.nrchop == 2:
                    inrech, inirch = fp.get_items(5, 2, fmt="i")
                else:
                    inrech = fp.get_items(5, 1, fmt="i")[0]
                    inirch = 0
                if inrech < 0 and sp == 0:
                    raise ValueError(
                        "INRECH specified to read results from previous "
                        "stress period, but this is the first stress period",
                    )
                # Either Item 6 or Item 7 may be read, but not both
                if self.nprch == 0 and inrech >= 0:
                    # 6: [RECH(NCOL,NROW)]
                    self.Rech[sp] = fp.get_array(6, shape2d, self._float_type)
                elif self.nprch > 0 and inrech > 0:
                    # 7: [Pname [Iname] [IRCHPF]]
                    raise NotImplementedError("PARAMETER not suported")
                elif inrech < 0:
                    # recharge rates from the preceding stress period are used
                    self.Rech[sp] = self.Rech[sp - 1]
                else:
                    raise ValueError("undefined logic for Data Set 6 or 7")
                if self.nrchop == 2 and inirch >= 0:
                    # 8: [IRCH(NCOL,NROW)]
                    self.Irch[sp] = fp.get_array(8, shape2d, "i")
            fp.check_end()
        except Exception as e:
            exec(fp.location_exception(e))
