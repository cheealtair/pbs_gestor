PBS-GESTOR
========================================================================

PBS Gestor is a daemon that reads the PBS accounting log messages and
sends them to PostgreSQL database. Once started, it will continue running
continuously in background, exiting only if killed/terminated by user
or the connection to database is lost.

To check that it is running, type 'top -c' or 'ps -ef' and look for 'pbs_gestor'.

To check results, look at the contents of PostgreSQL database, schema and tables:
'pbsjoblogsdb', 'schema' and 'pbsjob', 'pbsjobarr', correspondingly, by default,
but these names are settings to be set by user in the configuration file.
The daemon runs the infinite loop within pbsloghandler.py::readline()

------------------------------------------------------------------------
INTRODUCTION TO PEX
------------------------------------------------------------------------

The PBS_Gestor project provides a *.pex file - which is a Python executable,
 self-sufficient and requiring no installation of Python dependencies.
See: https://pex.readthedocs.io/en/stable/index.html 

PEX has been created successfully on Debian and RedHat-based systems
 and should work on other Linux systems as well.
The way to run the *.pex is described in 'Run' section below.

The following are instructions on building a *.pex file.
If you just want to run a *.pex file, you can safely skip to the 'Install' section.

To build a *.pex file, you need to install the python package 'pex', first.

The PBS_Gestor project is packaged in a standard manner 
using Python's setupscript setup.py and setup.cfg .
This makes it easy for 'pex' to package the Python code and all the required dependencies.

The instructions in the Makefile create a *.pex file packaged for multiple versions of Python.

To build for a specific Python version, please add to Makefile a specific instruction as follows,
- for example for Python 2.7:

ccbuild:
- 	rm -rf pbs_gestor.egg-info
- 	python2 -m pip wheel -w . . --isolated
- 	python -m pex . -f ./ -v -c gestor.py -o pbs_gestor_py2.7.8.pex --disable-cache --no-compile --platform="linux_x86_64-cp-27-cp27mu"
- 	rm -rf pbs_gestor.egg-info

To make, run:
- make ccbuild

To make pbs_gestor be seen as process name on top, edit *.pex file in binary mode, for example:
- vim -b ./pbs_gestor_py2.7.8.pex

Change the top line to the correct, full Python path (which will be different for each system):
- #!/opt/miniconda3/envs/bom-schema-py2/bin/python

OR
- #!/usr/bin/python

Alternatively, instead of editing binary *.pex file, run top as:
- top -c

------------------------------------------------------------------------
ABOUT SPHINX DOCUMENTATION
------------------------------------------------------------------------

* In addition to other setup requirements listed in setupscript setup.py,
   the Sphinx documentation building process requires the following packages:
  - Sphinx
  - rst2pdf
  
  How to make Sphinx documentation:
  - cd docs
  - make docs
* If the build process is unsuccessful and gives error about 'sphinx-build' being not found,
   then installation of Python package 'Sphinx' is required, as mentioned above.
* If the build process is successful, the pdf will be found in docs/build/ directory.
* Error message:
   - mkdir ../tmp
   - mkdir: cannot create directory `../tmp': File exists
   - make: *** [docs] Error 1

  during process of building documentation indicates
  that a previous failed attempt of making documentation has left files in incorrect location.
  
  The solution is:
   - cd docs
   - mv ../tmp/*.py ../
   - rmdir tmp
   - make docs
* Error message:
   - WARNING: autodoc: failed to import module u'gestor'; the following exception was raised:
   - Traceback (most recent call last):
   - TypeError: __init__() takes exactly 2 arguments (3 given)

  during generation of documentation indicates that the code was written for psycopg2 2.8 or higher;
  and running the code with psycopg2 version 2.7 or below causes error,
  because function "Identifier" takes only one argument in the older version of psycopg2.
  
  Solution:
   - Besides updating psycopg2, we can instead modify utils.py to specify schema explicitly,
     such as,
     - '{schema}.{table}'.format(schema=Identifier('schema'), table=Identifier('table'))

     instead of
     - '{table}'.format(table=Identifier('schema', 'table'))

------------------------------------------------------------------------
INSTALL PBS GESTOR
------------------------------------------------------------------------

PRE-REQUISITES:
* Python, version 2.7 or 3.6: https://www.python.org/
* PBS server accounting logs access
* PostgreSQL, version 9, such as 9.2.24 or 9.6.11: https://www.postgresql.org/

PRE-SETUP:

* PBS:
  - Start the PBS Server.
* PostgreSQL:
  - Set up host-based authentication (HBA) configuration as needed
    usually in /var/lib/pgsql/data/pg_hba.conf
  - Start PostgreSQL server.
  - Add PostgreSQL authentication data to PBS Gestor configuration file pbs_gestor_config.json ,
    such as: hostname, port, username, password, database name;
  - When you run PBS Gestor, it determines where to look for the file
    (default system location such as ~/.config/pbs_gestor/pbs_gestor_config.json ,
    or PBS_GESTOR_CONF if such environmental variable is set),
    prints out the location of configuration file to stdout,
    and if such file does not exist (for example, on the first run of PBS Gestor),
    then copies the default template to that location.
  - Besides username, password and database name, the configuration file also contains
    extra/back-up values 'supdatabase', 'supusername' and 'suppassword',
    which are not used by the program unless necessary, see examples below.
  - If the database doesn't exist, it will be created - user needs to have CREATEDB permissions,
    and it will be done by briefly connecting to 'supdatabase' ("postgres" by default) first .
  - If tablefunc extension isn't installed in the database, it will be created - by
    briefly connecting as super-user (see 'supusername' being "postgres" by default) first.
  - If tablefunc extension is installed in the database, but in a schema inaccessible to user,
    user will be granted access to the schema by briefly connecting as super-user first.
  - Tablefunc extension is required for Crosstab function to pivot a table,
    see details on PbsJobArr table and PbsRawFlatView view below.

------------------------------------------------------------------------
SETUP
------------------------------------------------------------------------

* Copy or move the `gestor` directory to any location accessible/preferable for you.

* If you haven't run the program before, run the program once, so that it writes out
  the default settings to a configuration file, and prints out location of the configuration file,
  with either of the following commands:
  - /path/to/pbs_gestor.pex
  - python /path/to/pbs_gestor.pex
  - /path/to/pbs_gestor.pex -c
  - python /path/to/pbs_gestor.pex -c

    On the first run - defined as when program doesn't find the config file at expected location,
  and has to create the configuration file with default settings - or if run with '-c' flag,
  the program doesn't establish a database connection,
  but just prints out location of the configuration file and exits, 
  so that user can put in the specific settings.

* The following components needs to be updated before starting the PBS Gestor daemon:
    - pbs_gestor_config.json - system related config needed for PBS
    Gestor plugin. Includes database authentication, logging configuration.
    Add PostgreSQL authentication data here, such as:
    hostname, port, username, password, database name

    Note - If you move pbs_gestor_config.json to a different location,
    please create or update the environment variable PBS_GESTOR_CONF 
    with the location of pbs_gestor_config.json .

------------------------------------------------------------------------
RUN
------------------------------------------------------------------------

* Start the Daemon script with one of the following commands:
  - /path/to/pbs_gestor.pex

  which should work as long as Python interpreter can be found at /usr/bin/python
  - python /path/to/pbs_gestor.pex
  - python3 /path/to/pbs_gestor.pex
  - python3.x /path/to/pbs_gestor.pex

  If you have source code of the program, it can also be run similarly with:
  - python /path/to/gestor.py

  but that requires installation of dependencies such as sqlalchemy - full list is inside setup.py

* Once started, the program can be seen in list of processes, such as in 'top -c' or 'ps -ef'.
  
  If started directly as:
  - /path/to/pbs_gestor.pex

  then the process name will be the same as name of the file, for example, 'pbs_gestor.7.8.',
  and it can be terminated with, for example, 'pkill pbs_gestor'.
  
  If started indirectly, such as:
  - python /path/to/pbs_gestor.pex

  then the process name will be the same as name of the Python interpreter used to run it,
  for example, 'python3', but it can still be identified with, for example,
  'ps aux | grep pbs_gestor'.

* To see help about the program, and examples of usage, run it with ' --help', for example:
  - /path/to/pbs_gestor.pex --help

  For example, you can supply the dates between which to process the logs as follows:
  - /path/to/pbs_gestor.pex -f lastscan -t today
  - /path/to/pbs_gestor.pex -f 20011231 -t 20190726

  Keep in mind that once processing of logs between the specified dates is finished,
  program doesn't exit; it opens today's log file and starts scanning today's logs,
  continuing indefinitely to process jobs' records as they arrive.

* The program outputs to stdout some minimal amount of information,
  such as: the range of dates in which it is going to process logs,
  and which log it is processing. Far more verbose output can be found in
  log file, which is usually written to /tmp/pbs_gestor_log - the setting can be configured
  inside pbs_gestor_config.json , under logger / handlers / rotating_file_handler.

------------------------------------------------------------------------
DATABASE
------------------------------------------------------------------------

* Run some pbs jobs - If all the configurations are set properly then
  you should see some records in the PostgreSQL database. The jobs are recorded
  in the tables 'pbsjob' and 'pbsjobarr' under schema 'schema' ,
  inside the database 'pbsjoblogsdb'; all these names are settings 
  specified inside pbs_gestor_config.json .

  - PbsJob table contains jobs and their attributes:
    name of the job, running time, vnode, user who started it, et cetera.
  - PbsJobArr contains job resources: assigned to jobs, or used by jobs.
      One column contains unique job identifier for relationship to PbsJob table,
      another column contains name of resource, and the last column contains value of resource.
  - Supplementary table PBSLog contains log handler records of which logs were processed when.
  
  Upon connecting to the PostgreSQL database
  - for example, with the command
   - psql -h hostname -p port -U username  -d databasename
   - which with default database connection settings would be
   - psql -h localhost -p 5432 -U postgres  -d pbsjoblogsdb

  you would be able to query the contents of the tables inside the database, such as:
  - SELECT * FROM schema.pbsjob;

  OR
  - SELECT * FROM schema.pbsjob WHERE ji_user='username';

  where username is name of a user whose job history you want to look up
  OR
  - SELECT count(*) FROM schema.pbsjob WHERE ji_user='username';

  if you want to count how many jobs the user has run in the past
  OR
  - any other SQL query
  
  Additionally, there are also two Views created, 'pbsrawflatview' and 'pbsrawflatviewjoin',
  inside the same schema as tables.
  - PbsFlatView contains a subset of information from PbsJobArr,
    pivoting the table with PostgreSQL's Crosstab function from Tablefunc extension
    so that requested and used resources would be organised into the following columns:
    'mem', 'ncpus', 'walltime', 'cput', 'nodect', 'cpupercent', et cetera
    instead of being contained in a Entity–attribute–value model as in PbsJobArr table.

    See: https://www.postgresql.org/docs/9.2/tablefunc.html#AEN152349

    Resources requested by job are prefixed with l,
    to be differentiated from resources used by job.

    It is also joined with PbsJob table so that Job ID would be available as one of the columns.
    See INNER JOIN on the following documentation page:

    https://www.postgresql.org/docs/9.2/queries-table-expressions.html#QUERIES-JOIN

    The values for the resources, such as ncpus or walltime, are cast to appropriate data types,
    so that arithmetic operations can be performed on them.

  These views can be queried similarly to tables, for example:
  - SELECT * FROM schema.pbsflatviewreqjoin WHERE l_nodect > 1;

  displays list of all jobs which requested/used more than one node.

------------------------------------------------------------------------
TROUBLESHOOT
------------------------------------------------------------------------

* For troubleshooting, try to connect to the database with the same settings
  (hostname, port, username, databasename) as are inside pbs_gestor_config.json file.
  - For ease of troubleshooting, application prints out the location from which it is reading
    the configuration file pbs_gestor_config.json . As noted earlier, if you move the file
    to a different location, please create or update the environment variable PBS_GESTOR_CONF 
    with the location of pbs_gestor_config.json .
  
  Check whether schema 'schema' exists by querying list of schemas with '\dn'
  command inside psql client.
  
  Check whether tables exist with '\dt schema.*' command.
  
  Check whether tablefunc extension is installed with the following command:
  - \dx+ tablefunc

  If it says 'Did not find any extension named "tablefunc"',
  then Tablefunc extension is not installed and Crosstab function is not available.
  If the Tablefunc extension is installed successfully,
  then there will be list of objects in extension "tablefunc",
  such as connectby, crosstab and normal_rand.
  OR
  - SELECT count(*) FROM information_schema.routines WHERE routine_name LIKE 'crosstab%'

  If it is 0, then Tablefunc extension is not installed and Crosstab function is not available.
  If it is above 0 - for example, 6 - then Crosstab function is available, which is good.

  If Tablefunc extension is installed, then you may also wish to check where it is installed:
  - SELECT routine_schema FROM information_schema.routines WHERE routine_name LIKE 'crosstab%'

  OR
  - SELECT specific_schema FROM information_schema.routines WHERE routine_name LIKE 'crosstab%'

  (which usually return the same result)
  to see which schema contains the installed Crosstab function.
  - Application expects this result to be either 'schema' or, failing that,
    something like 'public' so that the function is inside PostgreSQL's search_path.
    See: https://www.postgresql.org/docs/9.2/runtime-config-client.html#GUC-SEARCH-PATH
