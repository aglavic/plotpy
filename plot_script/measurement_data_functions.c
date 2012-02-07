/*
  Support functions for the measurement_data_structure python code.
  Intendet to speed up the slowest parts of the data treatment.
*/
#include <Python.h>
#include <arrayobject.h>
#include "measurement_data_functions.h"
#include <string.h>
#include <stdio.h>

/* 
  Initilaize stuff needed for python to use the functions
*/
/* ==== Set up the methods table ====================== */
static PyMethodDef measurement_data_functionsMethods[] = {
    {"string_from_data_matrix", string_from_data_matrix, METH_VARARGS},
    {NULL, NULL}     /* Sentinel - marks the end of this structure */
};

/* ==== Initialize the C_test functions ====================== */
// Module name must be measurement_data_functions in compile and linked 
void initmeasurement_data_functions()  {
    (void) Py_InitModule("measurement_data_functions", measurement_data_functionsMethods);
    import_array();  // Must be present for NumPy.  Called first after above line.
}

/*
  Below are the new functions that can be used from this extension module
*/

// Function to create lines of data columns as a string from an input matrix data
// Without further speedup this function doesn't improve the python version in 
//  measurement_data_structure by more the 20-30% so it won't be used.
static PyObject *string_from_data_matrix(PyObject *self, PyObject *args)
{
    PyArrayObject *input_matrix, *blank_line_array;  // The python objects to be extracted from the args
    char *seperator, *file_name;
    double **cinput_matrix, *cblank_line_array;           // The C matrices to be created to point to the 
                                    //   python matrices, cin and cout point to the rows
                                    //   of matin and matout, respectively
    int i,j,c;
    FILE *output_file;
    
    //+++++ Prepare the variables which are passed as arguments to the python function
    /* Parse tuples separately since args will differ between C fcns */
    if (!PyArg_ParseTuple(args, "ssO!O!", &file_name, &seperator, &PyArray_Type, &input_matrix,
        &PyArray_Type, &blank_line_array))  return NULL;
    if (NULL == input_matrix)  return NULL;
    if (NULL == blank_line_array)  return NULL;
    
    /* Check that objects are 'double' type and matrices
         Not needed if python wrapper function checks before call to this routine */
    if (not_doublematrix(input_matrix)) return NULL;
    //if (not_intmatrix(blank_line_array)) return NULL;
        
    /* Change contiguous arrays into C ** arrays (Memory is Allocated!) */
    cinput_matrix=pymatrix_to_Carrayptrs(input_matrix);
    cblank_line_array=pyvector_to_Carrayptrs(blank_line_array);
    
    /* Get matrix dimensions. */
    const int rows=input_matrix->dimensions[0];
    const int cols=input_matrix->dimensions[1];
    //------ Prepare the variables which are passed as arguments to the python function
    
    // open output_file to append data
    output_file=fopen(file_name ,"a+");
    
    j=0;
    // go through the data line by line and append it to the file
    for ( i=0; i<rows; i++)  {
      // write one line of data
      fprintf(output_file, "%f", cinput_matrix[i][0]);
      for ( c=1; c<cols; c++) {
        fprintf(output_file, "%s%f", seperator, cinput_matrix[i][c]);
      }
      // add newline
      fprintf(output_file, "\n");
      // append blank line
      if ( i == cblank_line_array[j] ) {
        fprintf(output_file,"\n");
        j++;
      }
    }
    fclose(output_file);    
    /* Free memory and return */
    free_Carrayptrs(cinput_matrix);
    return Py_BuildValue("s", "");
}


/* #### Vector Utility functions ######################### */

/* ==== Make a Python Array Obj. from a PyObject, ================
     generates a double vector w/ contiguous memory which may be a new allocation if
     the original was not a double type or contiguous 
  !! Must DECREF the object returned from this routine unless it is returned to the
     caller of this routines caller using return PyArray_Return(obj) or
     PyArray_BuildValue with the "N" construct   !!!
*/
PyArrayObject *pyvector(PyObject *objin)  {
    return (PyArrayObject *) PyArray_ContiguousFromObject(objin,
        NPY_DOUBLE, 1,1);
}
/* ==== Create 1D Carray from PyArray ======================
    Assumes PyArray is contiguous in memory.             */
double *pyvector_to_Carrayptrs(PyArrayObject *arrayin)  {
    int i,n;
    
    n=arrayin->dimensions[0];
    return (double *) arrayin->data;  /* pointer to arrayin data as double */
}
/* ==== Check that PyArrayObject is a double (Float) type and a vector ==============
    return 1 if an error and raise exception */ 
int  not_doublevector(PyArrayObject *vec)  {
    if (vec->descr->type_num != NPY_DOUBLE || vec->nd != 1)  {
        PyErr_SetString(PyExc_ValueError,
            "In not_doublevector: array must be of type Float and 1 dimensional (n).");
        return 1;  }
    return 0;
}

/* ==== Check that PyArrayObject is a double (Float) type and a matrix ==============
    return 1 if an error and raise exception */ 
int  not_doublematrix(PyArrayObject *mat)  {
    if (mat->descr->type_num != NPY_DOUBLE || mat->nd != 2)  {
        PyErr_SetString(PyExc_ValueError,
            "In not_doublematrix: array must be of type Float and 2 dimensional (n x m).");
        return 1;  }
    return 0;
}

/* ==== Free a double *vector (vec of pointers) ========================== */ 
void free_Carrayptrs(double **v)  {
    free((char*) v);
}

/* ==== Create Carray from PyArray ======================
    Assumes PyArray is contiguous in memory.
    Memory is allocated!                                    */
double **pymatrix_to_Carrayptrs(PyArrayObject *arrayin)  {
    double **c, *a;
    int i,n,m;
    
    n=arrayin->dimensions[0];
    m=arrayin->dimensions[1];
    c=ptrvector(n);
    a=(double *) arrayin->data;  /* pointer to arrayin data as double */
    for ( i=0; i<n; i++)  {
        c[i]=a+i*m;  }
    return c;
}

/* ==== Allocate a double *vector (vec of pointers) ======================
    Memory is Allocated!  See void free_Carray(double ** )                  */
double **ptrvector(long n)  {
    double **v;
    v=(double **)malloc((size_t) (n*sizeof(double)));
    if (!v)   {
        printf("In **ptrvector. Allocation of memory for double array failed.");
        exit(0);  }
    return v;
}
