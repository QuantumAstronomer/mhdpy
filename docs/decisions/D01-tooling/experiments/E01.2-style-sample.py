"""Code sample in the author's preferred style: input for experiment E01.2.

Verbatim excerpt (Grid.__init__), supplied 2026-10-09. Only this module
docstring and the enclosing class statement were added so that the file parses.
"""


class Grid:
    def __init__(
        self,
        n_cells: int | Sequence[int] | NDArray[np.integer],
        bound_lower: float | Sequence[float] | NDArray[np.integer | np.floating],
        bound_upper: float | Sequence[float] | NDArray[np.integer | np.floating],
        n_ghost: int = 2,
    ) -> None:
        """
        Parameters:
        =======================================================================
        n_cells: int | Sequence[int] | NDArray[np.integer], no default
            Number of interior (non-ghost) cells per direction. A plain int
            (or 0-d numpy array) gives a 1-D grid; a sequence or 1-D numpy
            array of length 1, 2, or 3 sets ndim to its length. Must be >= 1
            in every direction, and must match the form (scalar or sequence)
            and length of bound_lower and bound_upper.
        bound_lower: float | Sequence[float] | NDArray[np.integer | np.floating], no default
            Lower edge of the interior domain per direction, in coordinate
            space. Same form and length as n_cells.
        bound_upper: float | Sequence[float] | NDArray[np.integer | np.floating], no default
            Upper edge of the interior domain per direction, in coordinate
            space. Same form and length as n_cells. Must be strictly greater
            than bound_lower in every direction.
        n_ghost: int, default = 2
            Number of ghost cells padding the interior on each side, shared by
            every direction. Must be >= 0.

        Returns:
        =======================================================================
            None

        Raises:
        =======================================================================
        TypeError
            If an argument has the wrong type: a string anywhere, a
            non-integer (or bool) n_cells or n_ghost, or a non-real (or
            bool) bound (R9.3).
        ValueError
            If any argument violates a constraint listed under Parameters,
            or an array argument has more than one axis (R1.1). The message
            names the offending argument and, where relevant, the direction
            (R2.2 / R9.1).
        """

        # Strings are sequences in Python. However, they should not be passed,
        # hence we make an explicit check on the parameters.
        for name, value in (("n_cells", n_cells), ("bound_lower", bound_lower), ("bound_upper", bound_upper)):
            if isinstance(value, (str, bytes)):
                raise TypeError(f"{name} must be a number or a sequence of numbers, got: {type(value).__name__}.")

            # numpy arrays are accepted for convenience (R1.1): a 1-D array
            # counts as a sequence and a 0-d array as a bare scalar. An array
            # with more axes has no meaning here.
            if isinstance(value, np.ndarray) and value.ndim > 1:
                raise ValueError(f"{name} must be a scalar or a 1-D sequence, got: a {value.ndim}-D array.")

        # Requirement 1.1 specifies that n_cells, bound_lower, and bound_upper
        # must all agree on their type, i.e. they must be of the same type.
        # is_sequence() counts a 1-D numpy array as a sequence and a 0-d one
        # as a scalar; isinstance(value, Sequence) would count every array
        # as a scalar.
        if not (is_sequence(n_cells) == is_sequence(bound_lower) == is_sequence(bound_upper)):
            raise ValueError("n_cells, bound_lower, and bound_upper must be ALL scalars or ALL sequences, not a mix.")

        # Normalise all input parameters to tuples, whatever their input-form
        # used to be (scalar, list, tuple, etc.).
        n_cells     = to_tuple(n_cells)
        bound_lower = to_tuple(bound_lower)
        bound_upper = to_tuple(bound_upper)

        # Find the number of dimensions in each of the above tuples to make sure
        # they are consistent with one-another.
        ndim: int = len(n_cells)

        if not (len(n_cells) == len(bound_lower) == len(bound_upper)):
            raise ValueError(f"n_cells, bound_lower, and bound_upper must have the same length, got: "
                             f"n_cells = {len(n_cells)}, bound_lower = {len(bound_lower)}, bound_upper = {len(bound_upper)}.")

        # Number of dimensions can not exceed 3 and must be at least 1 to be
        # consistent with our physical world.
        if ndim not in (1, 2, 3):
            raise ValueError(f"Number of dimensions, i.e. length of the n_cells sequence, must either be 1, 2, or 3, got: {ndim}.")

        # Per-direction checks of validity of types and values
        for direction in range(ndim):
            # Check n_cells to be integer in every direction
            if not is_integer(value = n_cells[direction]):
                raise TypeError(f"n_cells[{direction}] must be an integer, got: {type(n_cells[direction]).__name__}.")

            # Check the upper and lower bounds to be a real value (not
            # necessarily > 0)
            for name, bound in (("bound_lower", bound_lower), ("bound_upper", bound_upper)):
                if not is_real(value = bound[direction]):
                    raise TypeError(f"{name}[{direction}] must be a real number, got: {type(bound[direction]).__name__}.")

                # inf and nan pass is_real(), and every comparison with nan is
                # False, so the ordering check below would not catch them
                # (R2.2).
                if not math.isfinite(bound[direction]):
                    raise ValueError(f"{name}[{direction}] must be finite, got: {bound[direction]}.")

            # Check the number of cells in each direction is larger than 0
            if n_cells[direction] < 1:
                raise ValueError(f"n_cells[{direction}] must be greater than or equal to 1, got: {n_cells[direction]}.")

            # Upper bound must be strictly greater than the lower bound to be
            # valid
            if bound_upper[direction] <= bound_lower[direction]:
                raise ValueError(f"bound_upper[{direction}] must be greater than bound_lower[{direction}], got: "
                                 f"bound_upper = {bound_upper[direction]} <= {bound_lower[direction]} = bound_lower.")

        # Make checks on the type and value of the ghost cells, i.e. must be a
        # non-negative integer.
        if not is_integer(value = n_ghost):
            raise TypeError(f"n_ghost must be an integer, got: {type(n_ghost).__name__}.")

        if n_ghost < 0:
            raise ValueError(f"n_ghost must be greater than or equal to 0, got: {n_ghost}.")

        # Store plain Python numbers, whatever numeric type was passed. numpy
        # scalars would otherwise leak into repr() ("np.int64(8)") and make
        # to_dict() unserializable by json, and a Fraction bound would turn
        # the coordinate arrays into object arrays (R1.2 / R8.2).
        n_cells     = tuple(int(n) for n in n_cells)
        bound_lower = tuple(float(bound) for bound in bound_lower)
        bound_upper = tuple(float(bound) for bound in bound_upper)
        n_ghost     = int(n_ghost)

        # Set the coordinate spacing per direction
        delta: tuple[float, ...] = tuple(
            (bound_upper[direction] - bound_lower[direction]) / n_cells[direction] for direction in range(ndim)
        )

        # Finally, store the normalised and validated variables under private
        # names; they are exposed through the read-only properties below (R8.3).
        self._ndim: int = ndim
        self._n_cells: tuple[int, ...] = n_cells
        self._bound_lower: tuple[float, ...] = bound_lower
        self._bound_upper: tuple[float, ...] = bound_upper
        self._n_ghost: int = n_ghost
        self._delta: tuple[float, ...] = delta

        # Coordinate arrays are computed once, here, and shared by reference
        # from then on (R4.5): faces() and centers() only look them up. The
        # centers are built from the faces, so the faces must come first.
        self._faces: tuple[NDArray[np.float64], ...] = tuple(self._compute_faces(direction) for direction in range(ndim))
        self._centers: tuple[NDArray[np.float64], ...] = tuple(self._compute_centers(direction) for direction in range(ndim))

        # Centroids depend on the geometry, so a bare Grid cannot compute
        # them here. They are computed on the first call to centroids(),
        # by the geometry's _compute_centroids(), and stored here from then
        # on (R10.5).
        self._centroids: tuple[NDArray[np.float64], ...] | None = None

        # The metric factors depend on the geometry as well, so, like the
        # centroids, they are computed on first use, by the geometry's
        # _compute_spacing(), _compute_face_area(), and _compute_cell_volume(),
        # and stored here from then on (R6.5).
        self._spacings: tuple[NDArray[np.float64], ...] | None = None
        self._face_areas: tuple[NDArray[np.float64], ...] | None = None
        self._cell_volume: NDArray[np.float64] | None = None

        # interior() and shift() store every result they compute, keyed by
        # their arguments, and return it again for the same arguments (R5.4).
        # A Grid never changes after construction (R8.3), so a stored result
        # can never go out of date.
        self._interior_cache: dict[tuple[object, ...], tuple[slice, ...]] = {}
        self._shift_cache: dict[tuple[object, ...], tuple[slice, ...]] = {}

        # min_spacing() and domain_volume() reduce the metric arrays over the
        # whole grid; since a Grid never changes (R8.3), they are computed on
        # the first call and stored here from then on (R6.3).
        self._min_spacing: float | None = None
        self._domain_volume: float | None = None

        # restrict() divides by the summed fine-cell volumes of every coarse
        # cell. Those depend only on the two grids, so they are computed once
        # per fine grid and stored here, keyed by the fine grid (Grids are
        # hashable, R8.1, and equal grids have equal volumes).
        self._restriction_volume_sums: dict[Grid, NDArray[np.float64]] = {}

        # prolong() multiplies the neighbor differences of the coarse data by
        # weights that depend only on centroid positions, so only on the two
        # grids as well. They are computed once per coarse grid and stored
        # here, keyed by the coarse grid, just like the volume sums above.
        self._prolongation_weights: dict[Grid, tuple[tuple[NDArray[np.float64], ...], ...]] = {}
