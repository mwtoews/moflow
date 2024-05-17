import numpy as np

from .base import MFPackage
from .reader import MFFileReader


class _Discretization(MFPackage):
    """Abstract discretization file."""

    @property
    def nlay(self):
        """Number of layers in the model grid."""
        return getattr(self, "_nlay", None)

    @nlay.setter
    def nlay(self, value) -> None:
        if value is not None:
            try:
                value = int(value)
                assert value > 0
            except:
                raise ValueError(f"invalid 'nlay': {value!r}")
        self._nlay = value

    @property
    def nper(self):
        """Number of stress periods in the simulation."""
        return getattr(self, "_nper", None)

    @nper.setter
    def nper(self, value) -> None:
        if value is not None:
            try:
                value = int(value)
                assert value > 0
            except:
                raise ValueError(f"invalid 'nper': {value!r}")
        self._nper = value

    @property
    def itmuni(self):
        """Time unit of model data, which must be consistent for all data
        values that involve time.
        """
        return getattr(self, "_itmuni", 0)

    @itmuni.setter
    def itmuni(self, value) -> None:
        if value is not None:
            try:
                assert int(value) is not None
            except:
                raise ValueError(f"invalid 'itmuni': {value!r}")
        self._itmuni = value

    _itmuni_str = {0: "?", 1: "s", 2: "min", 3: "h", 4: "d", 5: "y"}
    _str_itmuni = {v: k for k, v in _itmuni_str.items()}

    @property
    def itmuni_str(self):
        """Time unit character(s) from ITMUNI.
        (0) ? - undefined
        (1) s - seconds
        (2) min - minutes
        (3) h - hours
        (4) d - days
        (5) y - years.
        """
        try:
            return self._itmuni_str[self.itmuni]
        except KeyError:
            raise ValueError(f"invalid 'itmuni': {self.itmuni!r}")

    @itmuni_str.setter
    def itmuni_str(self, value) -> None:
        """Set time unit ITMUNI; no other dat is modified."""
        d = dict((v, k) for k, v in self._str_itmuni.iteritems())
        try:
            self.itmuni = d[value]
        except KeyError:
            raise ValueError(f"invalid 'itmuni_str': {value!r}")

    @property
    def lenuni(self):
        """Length unit of model data, which must be consistent for all data
        values that involve length.
        """
        return getattr(self, "_lenuni", 0)

    @lenuni.setter
    def lenuni(self, value) -> None:
        if value is not None:
            try:
                assert int(value) is not None
            except:
                raise ValueError(f"invalid 'lenuni': {value!r}")
        self._lenuni = value

    _lenuni_str = {0: "?", 1: "ft", 2: "m", 3: "cm"}
    _str_lenuni = {v: k for k, v in _lenuni_str.items()}

    @property
    def lenuni_str(self):
        """Length unit character(s) from lenuni.
        (0) ?  - undefined
        (1) ft - feet
        (2) m  - meters
        (3) cm - centimeters.
        """
        try:
            return self._lenuni_str[self.lenuni]
        except KeyError:
            raise ValueError(f"invalid 'lenuni': {self.lenuni}")

    @lenuni_str.setter
    def lenuni_str(self, value) -> None:
        try:
            self.lenuni = self._str_lenuni[value]
        except KeyError:
            raise ValueError(f"invalid 'lenuni_str': {value!r}")

    def _read_stress_period_data(self, fp, data_set_num) -> None:
        startln = fp.lineno + 1
        # PERLEN NSTP TSMULT Ss/tr
        stress_period_dtype = np.dtype(
            [
                ("perlen", self._float_type),
                ("nstp", "i"),
                ("tsmult", self._float_type),
                ("sstr", "|S2"),
            ],
        )
        self.stress_period = np.zeros(self.nper, dtype=stress_period_dtype)
        names = self.stress_period.dtype.names
        for row in self.stress_period:
            dat = fp.get_named_items(data_set_num, names)
            for name in names:
                row[name] = dat[name]
        for name in names:
            setattr(self, name, self.stress_period[name])
        fp.logger.debug(
            "%s:read %d stress period%s from line %d to %d",
            fp.data_set_num,
            len(self.stress_period),
            "" if len(self.stress_period) == 1 else "s",
            startln,
            fp.lineno,
        )


class DIS(_Discretization):
    """Discretization file."""

    @property
    def nrow(self):
        """Number of rows in the model grid."""
        return getattr(self, "_nrow", None)

    @nrow.setter
    def nrow(self, value) -> None:
        if value is not None:
            try:
                value = int(value)
                assert value > 0
            except:
                raise ValueError(f"invalid 'nrow': {value!r}")
        self._nrow = value

    @property
    def ncol(self):
        """Number of columns in the model grid."""
        return getattr(self, "_ncol", None)

    @ncol.setter
    def ncol(self, value) -> None:
        if value is not None:
            try:
                value = int(value)
                assert value > 0
            except:
                raise ValueError(f"invalid 'ncol': {value!r}")
        self._ncol = value

    @property
    def shape2d(self):
        """Array shape in 2D: (nrow, ncol)."""
        return (self.nrow, self.ncol)

    @property
    def shape3d(self):
        """Array shape in 3D: (nlay, nrow, ncol)."""
        return (self.nlay, self.nrow, self.ncol)

    @property
    def shape4d(self):
        """Array shape in 4D: (nper, nlay, nrow, ncol)."""
        return (self.nper, self.nlay, self.nrow, self.ncol)

    @property
    def Area(self):
        """Returns 2D array of grid areas."""
        rows = self.delr.astype("d").reshape((1,) + self.delr.shape)
        cols = self.delc.astype("d").reshape(self.delc.shape + (1,))
        return rows * cols

    @property
    def Volume(self):
        """Returns 3D array of grid volumes."""
        elevs = np.vstack(
            (self.Top.astype("d").reshape((1,) + self.Top.shape), self.BOTM.astype("d")),
        )
        heights = -np.diff(elevs, axis=0)
        area = self.area
        area.shape = (1,) + area.shape
        return area * heights

    @property
    def top_left(self):
        """Top left coordinate pair (X, Y) for corner of grid."""
        value = getattr(self, "_top_left", None)
        if value is None:
            self._top_left = value = (0.0, 0.0)
            self._logger.warning("'top_left' is not set; using %s", value)
        return value

    @top_left.setter
    def top_left(self, value) -> None:
        if value is not None:
            try:
                assert len(value) == 2
            except:
                raise ValueError(
                    "invalid 'top_left': must be a tuple pair "
                    f"(X, Y); found: {value!r}",
                )
        self._top_left = value

    @property
    def geotransform(self):
        """Get GeoTransform for exporting rasters with GDAL.

        Requires self.top_left_X and self.top_left_Y to be set,
        as MODFLOW grids are locally defined from (0, 0).

        Returns a six-item tuple of the format:
            [0] top left x
            [1] w-e pixel resolution
            [2] rotation, 0 if image is "north up"
            [3] top left y
            [4] rotation, 0 if image is "north up"
            [5] n-s pixel resolution
        for example: (2779000.0, 100.0, 0.0, 6164500.0, 0.0, -100.0)
        """
        # Determine GeoTransform
        dx = self.delc.mean()
        if self.delc.min() != self.delc.max():
            self._logger.warning(
                "'delc' values range from %s to %s; using mean of %s",
                self.delc.min(),
                self.delc.max(),
                dx,
            )
        dy = self.delr.mean()
        if self.delr.min() != self.delr.max():
            self._logger.warning(
                "'delr' values range from %s to %s; using mean of %s",
                self.delr.min(),
                self.delr.max(),
                dy,
            )
        top_left_X, top_left_Y = self.top_left
        return (
            top_left_X,  # top left x
            dx,
            0.0,  # w-e pixel resolution; rotation
            top_left_Y,  # top left y
            0.0,
            -dy,
        )  # rotation, n-s pixel resolution

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: nper={self.nper}, nlay={self.nlay}, nrow={self.nrow}, ncol={self.ncol}>"

    def read(self, fpath=None) -> None:
        """Read DIS file."""
        fp = MFFileReader(fpath, self)
        try:
            # 0: [#Text]
            fp.read_text(0)
            # 1: NLAY NROW NCOL NPER ITMUNI LENUNI
            fp.read_named_items(
                1, ["nlay", "nrow", "ncol", "nper", "itmuni", "lenuni"], "i",
            )
            # 2: LAYCBD(NLAY)
            dat = fp.get_items(2, num_items=self.nlay, multiline=True)
            self.laycbd = [int(x) for x in dat]
            if self.nlay > 1 and self.laycbd[-1]:
                self._logger.error(
                    "%d:%d:LAYCBD for the bottom layer must be '0'; found %r",
                    fp.data_set_num,
                    fp.lineno,
                    dat[-1],
                )
            # 3: DELR(NCOL) - U1DREL
            self.delr = fp.get_array(3, self.ncol, self._float_type)
            # 4: DELC(NROW) - U1DREL
            self.delc = fp.get_array(4, self.nrow, self._float_type)
            # 5: Top(NCOL,NROW) - U2DREL
            self.top = fp.get_array(5, self.shape2d, self._float_type)
            # 6: BOTM(NCOL,NROW) - U2DREL
            # for each model layer and Quasi-3D confining bed
            num_botm = self.nlay
            if self.nlay > 1:
                num_botm += sum(self.laycbd)
            self.botm = np.empty((num_botm,) + self.shape2d, self._float_type)
            for ibot in range(num_botm):
                n = "6:L" + str(ibot + 1)
                self.botm[ibot, :, :] = fp.get_array(n, self.shape2d, self._float_type)
            # FOR EACH STRESS PERIOD
            # 7: PERLEN NSTP TSMULT Ss/tr
            self._read_stress_period_data(fp, 7)
            fp.check_end()
        except Exception as e:
            exec(fp.location_exception(e))


class DISU(_Discretization):
    """Unstructured Discretization file."""

    @property
    def nodes(self):
        """Number of nodes in the model grid."""
        return getattr(self, "_nodes", None)

    @nodes.setter
    def nodes(self, value) -> None:
        if value is not None:
            try:
                value = int(value)
                assert value > 0
            except:
                raise ValueError(f"invalid 'nodes': {value!r}")
        self._nodes = value

    @property
    def njag(self):
        """Total number of connections of an unstructured grid."""
        return getattr(self, "_njag", None)

    @njag.setter
    def njag(self, value) -> None:
        if value is not None:
            try:
                value = int(value)
                assert value > 0
            except:
                raise ValueError(f"invalid 'njag': {value!r}")
        self._njag = value

    @property
    def njags(self):
        """Total number of non-zero entries for symmetric input of symmetric
        flow properties between cells; njags = (njag - nodes)/2.
        """
        if ((self.njag - self.nodes) % 2) != 0:
            self._logger.warning("'njags' determined from odd values")
        return int((self.njag - self.nodes) / 2)

    @property
    def ivsd(self):
        """Vertical sub-discretization index, either 0, 1, or -1.
        *  0: no sub-discretization of layers within the model domain
        *  1: there could be vertical sub-discretization of layers
        * -1: no vertical sub-discretization of layers, and horizontal
            discretization of all layers is the same.
        """
        return getattr(self, "_ivsd", None)

    @ivsd.setter
    def ivsd(self, value) -> None:
        if value not in (None, 0, 1, -1):
            raise ValueError("invalid 'ivsd: must be 0, 1, or -1")
        self._ivsd = value

    @property
    def idsymrd(self):
        """Flag indicating if the finite-volume connectivity, either 0, or 1.
        * 0: finite-volume connectivity information is provided for the
            full matrix of the porous matrix grid-block connections of an
            unstructured grid
        * 1: finite-volume connectivity information is provided only for
            the upper triangular portion of the porous matrix grid-block
            connections within the unstructured grid.
        """
        return getattr(self, "_idsymrd", None)

    @idsymrd.setter
    def idsymrd(self, value) -> None:
        if value not in (None, 0, 1):
            raise ValueError("invalid 'idsymrd: must be 0, or 1")
        self._idsymrd = value

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: nper={self.nper}, nlay={self.nlay}, nodes={self.nodes}, njag={self.njag}, ivsd={self.ivsd}>"

    def read(self, fpath=None) -> None:
        """Read DISU file."""
        fp = MFFileReader(fpath, self)
        try:
            # 0: [#Text]
            fp.read_text(0)
            # 1: NODES NLAY NJAG IVSD NPER ITMUNI LENUNI IDSYMRD
            fp.read_named_items(
                1,
                [
                    "nodes",
                    "nlay",
                    "njag",
                    "ivsd",
                    "nper",
                    "itmuni",
                    "lenuni",
                    "idsymrd",
                ],
                "i",
            )
            # 2: LAYCBD(NLAY)
            dat = fp.get_items(2, num_items=self.nlay, multiline=True)
            self.laycbd = [int(x) for x in dat]
            if self.nlay > 1 and self.laycbd[-1]:
                self._logger.error(
                    "%d: LAYCBD for the bottom layer must be 0; found %s",
                    fp.lineno,
                    dat[-1],
                )
            # 3: NODELAY(NLAY) - U1DINT
            self.Nodelay = fp.get_array(3, self.nlay, "i")
            # 4: Top(NDSLAY) - U1DREL
            self.Top = []
            for ilay, ndslay in enumerate(self.Nodelay):
                n = "4:L" + str(ilay + 1)
                self.Top.append(fp.get_array(n, ndslay, self._float_type))
            # 5: Bot(NDSLAY) - U1DREL
            self.Bot = []
            for ilay, ndslay in enumerate(self.Nodelay):
                n = "5:L" + str(ilay + 1)
                self.Bot.append(fp.get_array(n, ndslay, self._float_type))
            # 6: Area(NDSLAY) - U1DREL
            if self.ivsd == -1:
                self.Area = fp.get_array(6, self.Nodelay[0], self._float_type)
            else:
                self.Area = []
                for ilay, ndslay in enumerate(self.Nodelay):
                    n = "6:L" + str(ilay + 1)
                    self.Area.append(fp.get_array(n, ndslay, self._float_type))
            # 7: IAC(NODES) - U1DINT
            self.Iac = fp.get_array(7, self.nodes, "i")
            # 8: JA(NJAG) - U1DINT
            self.Ja = fp.get_array(8, self.njag, "i")
            if self.ivsd == 1:
                # 9: IVC(NJAG) - U1DINT
                self.Ivc = fp.get_array(9, self.njag, "i")
            else:
                fp.logger.debug("9:skipped; ivsd=%s", self.ivsd)
            if self.idsymrd == 1:
                # 10a: CL1(NJAG) - U1DREL
                self.Cl1 = fp.get_array("10a", self.njags, self._float_type)
                # 10b: CL2(NJAG) - U1DREL
                self.Cl2 = fp.get_array("10b", self.njags, self._float_type)
                fp.logger.debug("11:skipped; idsymrd=%s", self.idsymrd)
            elif self.idsymrd == 0:
                fp.logger.debug("10:skipped; idsymrd=%s", self.idsymrd)
                # 11: CL12(NJAG) - U1DREL
                self.Cl12 = fp.get_array(11, self.njag, self._float_type)
            else:
                fp.logger.debug("10 to 11:skipped; idsymrd=%s", self.idsymrd)
            # 12: FAHL(NJAG/NJAGS) - U1DREL
            self.Fahl = fp.get_array(12, self.njag, self._float_type)

            # FOR EACH STRESS PERIOD
            # 13: PERLEN NSTP TSMULT Ss/Tr
            self._read_stress_period_data(fp, 13)
            fp.check_end()
        except Exception as e:
            exec(fp.location_exception(e))
