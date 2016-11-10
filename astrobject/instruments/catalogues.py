#! /usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
from sncosmo import get_bandpass

from .baseinstrument import Catalogue, coordinates,units
# -- here load all the object that could be parsed
from ..utils.tools import kwargs_update
from ..utils.decorators import _autogen_docstring_inheritance, make_method



# ============================= #
#                               #
# Quick Catalogue Study         #
#                               #
# ============================= #
@make_method(Catalogue)
def stellar_density( catalogue, mask=None,
                     angdist=0.1*units.degree):
    """ get the stellar density of the catalogue

    Parameters
    ----------
    catalogue: [Catalogue]
        the catalogue for which you want the stellar density.
    
    mask: [bool-array] -optional-
        boolean array for instance generated by the `get_mask` catalogue method.
        By default, (mask=None) the mask will be stars_only=True.
        For instance, a catmag_mask could be a great idea.
        
    Return
    ------
    float
    """
    mask     = catalogue.get_mask(stars_only=True) if mask is None else mask
    ra,dec   = catalogue.get(["ra","dec"], mask= mask)
    skyradec = coordinates.SkyCoord(ra=ra,dec=dec, unit="deg")
    
    return np.bincount(skyradec.search_around_sky(skyradec,angdist)[0])
    


#################################
#                               #
# All Sky GAIA: Catalogue       #
#                               #
#################################
def fetch_gaia_catalogue(center, radius, extracolumns=[], column_filters={}, **kwargs):
    """ "query the gaia catalogue thought Vizier (I/337, DR1) using astroquery.
    This function requieres an internet connection.

    Parameters
    ----------
    center: [string] 'ra dec'
        position of the center of the catalogue to query.

    radius: [string] 'value unit'
        radius of the region to query. For instance '1d' means a
        1 degree raduis

    extracolumns: [list-of-string] -optional-
        Add extra column from the V/139 catalogue that will be added to
        the basic query (default: position, ID, object-type, magnitudes)

    column_filters: [dict] -optional-
        Selection criterium for the queried catalogue.

    **kwargs goes to astroquery.vizier.Vizier
    
    Returns
    -------
    SDSSCatalogue (child of Catalogue)
    
    """
    try:
        from astroquery import vizier
    except:
        raise ImportError("install astroquery. (pip install astroquery)")

    #   Basic Info
    # --------------
    columns = ["RA_ICRS","DE_ICRS","e_RA_ICRS","e_DE_ICRS","Source","Dup",
               "o_<Gmag>","<FG>","e_<FG>","<Gmag>","Var"]
        
    columns = columns+extracolumns
    column_quality = {} # Nothing there yet
    
    c = vizier.Vizier(catalog="I/337/gaia", columns=columns,
                      column_filters=kwargs_update(column_quality,**column_filters),
                      **kwargs)
    c.ROW_LIMIT = "unlimited"
    
    t = c.query_region(center,radius=radius).values()[0]
    
    cat = GAIACatalogue(empty=True)
    cat.create(t.columns ,None,
               key_ra="RA_ICRS",key_dec="DE_ICRS")
    return cat


class GAIACatalogue( Catalogue ):

    source_name = "Gaia"
    
    def __init__(self, catalogue_file=None, empty=False,
                 key_mag="__Gmag_", key_magerr="__e_Gmag_",
                 key_ra=None, key_dec=None, **kwargs):
        """
        """
        self.__build__(data_index=0,key_mag=key_mag,
                       key_magerr=key_magerr,key_id="Source",
                       key_ra=key_ra,key_dec=key_dec)
        if empty:
            return
        
        self.load(catalogue_file,**kwargs)
    
    @_autogen_docstring_inheritance(Catalogue.set_mag_keys,"Catalogue.set_mag_keys")
    def set_mag_keys(self,key_mag,key_magerr):
        #
        # add lbda def
        #
        super(GAIACatalogue,self).set_mag_keys(key_mag,key_magerr)
        if "G" in key_mag:
            self.lbda = 6730

#################################
#                               #
# BASIC SDSS: Catalogue         #
#                               #
#################################
def fetch_sdss_catalogue(center, radius, extracolumns=[],column_filters={"rmag":"5..25"},**kwargs):
    """ query online sdss-catalogue in Vizier (V/139, DR9) using astroquery.
    This function requieres an internet connection.
    
    Parameters
    ----------
    center: [string] 'ra dec'
        position of the center of the catalogue to query.

    radius: [string] 'value unit'
        radius of the region to query. For instance '1d' means a
        1 degree raduis

    extracolumns: [list-of-string] -optional-
        Add extra column from the V/139 catalogue that will be added to
        the basic query (default: position, ID, object-type, magnitudes)

    column_filters: [dict] -optional-
        Selection criterium for the queried catalogue.

    **kwargs goes to astroquery.vizier.Vizier
    
    Returns
    -------
    SDSSCatalogue (child of Catalogue)
    """
    from .sdss import SDSS_INFO
    try:
        from astroquery import vizier
    except:
        raise ImportError("install astroquery. (pip install astroquery)")
    
    # -----------
    # - DL info
    columns = ["cl","objID",#"SDSS9",
               "RAJ2000","e_RAJ2000","DEJ2000","e_DEJ2000",
               #"ObsDate","Q"#"mode",
               ]
    for band in SDSS_INFO["bands"]:
        columns.append("%smag"%band)
        columns.append("e_%smag"%band)
    
    columns = columns+extracolumns
    column_quality = {"mode":"1","Q":"2.3"}
    # - WARNING if discovered that some of the bandmag were missing if too many colums requested
    c = vizier.Vizier(catalog="V/139", columns=columns,
                      column_filters=kwargs_update(column_quality,**column_filters),
                      **kwargs)
    c.ROW_LIMIT = "unlimited"
    #try:
    t = c.query_region(center,radius=radius).values()[0]
    #except :
    #    raise IOError("Error while querying the given coords. You might not have an internet connection")
    
    cat = SDSSCatalogue(empty=True)
    cat.create(t.columns,None,
               key_class="cl",value_star=6,key_id="objID",
               key_ra="RAJ2000",key_dec="DEJ2000")
    return cat

# ------------------- #
# - SDSS CATALOGUE  - #
# ------------------- #
class SDSSCatalogue( Catalogue ):
    """
    """
    source_name = "SDSS"
    
    def __init__(self, catalogue_file=None,empty=False,
                 value_star=6,key_mag=None,key_magerr=None,
                 key_ra=None,key_dec=None,**kwargs):
        """
        """
        self.__build__(data_index=2,key_mag=key_mag,
                       key_magerr=key_magerr,key_id="objID",
                       key_ra=key_ra,key_dec=key_dec)
        if empty:
            return
        
        self.load(catalogue_file,**kwargs)
        self.set_starsid("cl",6)
    
    @_autogen_docstring_inheritance(Catalogue.set_mag_keys,"Catalogue.set_mag_keys")
    def set_mag_keys(self,key_mag,key_magerr):
        #
        # add lbda def
        #
        super(SDSSCatalogue,self).set_mag_keys(key_mag,key_magerr)
        if key_mag is not None:
            bandpass = get_bandpass("sdss%s"%key_mag[0])
            self.lbda = bandpass.wave_eff
    
#################################
#                               #
# BASIC 2MASS: Catalogue        #
#                               #
#################################
def fetch_2mass_catalogue(center,radius,extracolumns=[],
                          column_filters={"Jmag":"5..30"},**kwargs):
    """ query online 2mass-catalogue in Vizier (II/246) using astroquery.
    This function requieres an internet connection.
    
    Parameters
    ----------
    center: [string] 'ra dec'
        position of the center of the catalogue to query.

    radius: [string] 'value unit'
        radius of the region to query. For instance '1d' means a
        1 degree raduis

    extracolumns: [list-of-string] -optional-
        Add extra column from the II/246 catalogue that will be added to
        the basic query (default: position, ID, magnitudes)

    column_filters: [dict] -optional-
        Selection criterium for the queried catalogue.

    **kwargs goes to astroquery.vizier.Vizier
    
    Returns
    -------
    MASSCatalogue (child of Catalogue)
    """
    try:
        from astroquery import vizier
    except:
        raise ImportError("install astroquery. (pip install astroquery)")
    
    # -----------
    # - DL info
    columns = ["2MASS",
               "RAJ2000","DEJ2000",
               ]
        
    for band in ["J","H","K"]:
        columns.append("%smag"%band)
        columns.append("e_%smag"%band)
    
    columns = columns+extracolumns
    # - WARNING if discovered that some of the bandmag were missing if too many colums requested
    c = vizier.Vizier(catalog="II/246", columns=columns, column_filters=column_filters,
                      **kwargs)
    c.ROW_LIMIT = 100000
    try:
        t = c.query_region(center,radius=radius).values()[0]
    except:
        raise IOError("Error while querying the given coords. You might not have an internet connection")
    
    cat = MASSCatalogue(empty=True)
    cat.create(t.columns,None,
               key_class="PointSource",value_star=None,
               key_ra="RAJ2000",key_dec="DEJ2000")
    return cat

# ------------------- #
# - 2MASS CATALOGUE - #
# ------------------- #
class MASSCatalogue( Catalogue ):
    """
    """
    source_name = "2MASS"
    
    def __init__(self, catalogue_file=None,empty=False,
                 key_mag=None,key_magerr=None,key_ra=None,key_dec=None,**kwargs):
        """
        """
        self.__build__(data_index=2,key_mag=key_mag,
                       key_magerr=key_magerr,
                       key_ra=key_ra,key_dec=key_dec)
        if empty:
            return
        
        self.load(catalogue_file,**kwargs)        
    
    @_autogen_docstring_inheritance(Catalogue.set_mag_keys,"Catalogue.set_mag_keys")
    def set_mag_keys(self,key_mag,key_magerr):
        #
        # add lbda def
        #
        super(MASSCatalogue,self).set_mag_keys(key_mag,key_magerr)
        if key_mag is not None:
            if key_mag == "Jmag":
                self.lbda = 12350
            elif key_mag == "Hmag":
                self.lbda = 16620
            elif key_mag == "Kmag":
                self.lbda = 21590
            else:
                raise ValueError("'%s' is not a recognized 2MASS band")
    # ----------------------- #
    # -  CATALOGUE HACK     - #
    # ----------------------- #
    @property
    def mag(self):
        if not self._is_keymag_set_(verbose=False):
            print "No 'key_mag' defined. J band used by default. -> To change: set_mag_keys() "
            self.set_mag_keys("Jmag","e_Jmag")
            
        return super(MASSCatalogue,self).mag

    # ------------------------------
    # - All points are Point Sources
    @property
    def _objecttype(self):
        print "All Loaded data are %s"%self._build_properties["key_class"]
        return np.ones(self.nobjects)

    @property
    def starmask(self):
        """ This will tell which of the datapoints is a star
        Remark, you need to have defined key_class and value_star
        in the __build_properties to be able to have access to this mask
        ==> In 2MASS PointSource catalogue, all data are stars
        """
        return np.ones(self.nobjects_in_fov,dtype="bool")  #not self.fovmask already in objecttype


#################################
#                               #
# BASIC WISE: Catalogue         #
#                               #
#################################
def fetch_wise_catalogue(center,radius,extracolumns=[],column_filters={"Jmag":"5..30"}):
    """ query online wise-catalogue in Vizier (II/328) using astroquery.
    This function requieres an internet connection.
    
    Parameters
    ----------
    center: [string] 'ra dec'
        position of the center of the catalogue to query.

    radius: [string] 'value unit'
        radius of the region to query. For instance '1d' means a
        1 degree raduis

    extracolumns: [list-of-string] -optional-
        Add extra column from the II/328 catalogue that will be added to
        the basic query (default: position, ID, magnitudes)

    column_filters: [dict] -optional-
        Selection criterium for the queried catalogue.

    **kwargs goes to astroquery.vizier.Vizier
    
    Returns
    -------
    WISECatalogue (child of Catalogue)
    """
    try:
        from astroquery import vizier
    except:
        raise ImportError("install astroquery. (pip install astroquery)")
    
    # -----------
    # - DL info
    columns = ["AllWISE","ID",
               "RAJ2000","DEJ2000",
               ]
        
    for band in ["J","H","K","W1","W2","W3","W4"]:
        columns.append("%smag"%band)
        columns.append("e_%smag"%band)
    
    columns = columns+extracolumns
    # - WARNING if discovered that some of the bandmag were missing if too many colums requested
    c = vizier.Vizier(catalog="II/328", columns=columns, column_filters=column_filters,
                      **kwargs)
    c.ROW_LIMIT = 100000
    try:
        t = c.query_region(center,radius=radius).values()[0]
    except:
        raise IOError("Error while querying the given coords. You might not have an internet connection")
    
    cat = WISECatalogue(empty=True)
    cat.create(t.columns,None,
               key_class="ToBeDone",value_star=None,
               key_ra="RAJ2000",key_dec="DEJ2000")
    return cat

# ------------------- #
# - WISE CATALOGUE  - #
# ------------------- #
class WISECatalogue( Catalogue ):
    """
    """
    source_name = "WISE"
    
    def __init__(self, catalogue_file=None,empty=False,
                 key_mag=None,key_magerr=None,key_ra=None,key_dec=None,**kwargs):
        """
        """
        
        print "STAR vs. GALAXY PARSING NOT READY YET"
        
        self.__build__(data_index=2,key_mag=key_mag,
                       key_magerr=key_magerr,
                       key_ra=key_ra,key_dec=key_dec)
        if empty:
            return
        
        self.load(catalogue_file,**kwargs)  
    
    @_autogen_docstring_inheritance(Catalogue.set_mag_keys,"Catalogue.set_mag_keys")
    def set_mag_keys(self,key_mag,key_magerr):
        #
        # add lbda def
        #
        super(WISECatalogue,self).set_mag_keys(key_mag,key_magerr)
        if key_mag is not None:
            self.lbda = "TO BE DEFINED"
            
    @property
    def mag(self):
        if not self._is_keymag_set_(verbose=False):
            print "No 'key_mag' defined. W1 band used by default. -> To change: set_mag_keys() "
            self.set_mag_keys("W1mag","e_W1mag")
            
        return super(WISECatalogue,self).mag

    
