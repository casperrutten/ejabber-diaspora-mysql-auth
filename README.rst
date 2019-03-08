***********************
ejabberd diaspora* auth
***********************

requirements
------------

* diaspora* mysql/mariadb database
* ejabberd server
* python3 

features
--------

* authentication against *Diaspora database
* parsing *Diaspora config files for database credentials and pepper
* support for DIASPORA_DIR environmental variable (_/home/diaspora/diaspora_ by default)

installation
------------

    pip install ejabberd_diaspora_auth

ejabberd configuration
----------------------

    auth_method: external
    
    extauth_program: "/usr/bin/ejabber-diaspora_auth.py"



