/* Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others. See
   the file COPYRIGHT for details. */

/* Note: Make sure hash output exactly matches hash_.py. */

/* FIXME: This is not the most robust program. Patches to improve this are
   super welcome. In particular, I think it only compiles with gcc, which
   makes me sad.

   One thing I'm not terribly worried about is not checking for malloc()
   errors. We allocate very little memory, and given memory overcommit on
   modern OS'es, the odds of a failure at malloc() time are slim. */

#define _GNU_SOURCE  // for asprintf()
#include <errno.h>
#include <stdio.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>


/** Constants **/

/* We use a relatively large output buffer size of 512K to be prepared for
   filesystems that use large blocks (e.g., Panasas, some RAID). (See also
   OUTPUT_BUFSIZE in lib/qr/base.py.)

   FIXME: this parameter has not been tuned experimentally. */
#define OUTPUT_BUFSIZE 524288


/** Prototypes **/

void fatal(char * msg, ...);
unsigned int hash(char * str, char * end);
void output_close(FILE * out[], int ct);
FILE ** output_open(char * basename, int ct);
void split(FILE ** out, int output_ct);
void usage();


/** Main **/

int main(int argc, char * argv[])
{
   int output_ct;
   FILE ** out;

   // parse args
   if (argc != 3)
      usage();
   output_ct = atoi(argv[1]);
   if (output_ct < 1)
      fatal("invalid number of output files: %d", output_ct);
   if (strlen(argv[2]) == 0)
      fatal("length of BASENAME cannot be 0");

   // do the work
   out = output_open(argv[2], output_ct);
   split(out, output_ct);
   output_close(out, output_ct);

   return EXIT_SUCCESS;
}


/** Supporting functions **/

/* Exit with failure after printing message followed by newline to stderr.
   Arguments are passed unchanged to fprintf(). */
void fatal(char * fmt, ...)
{
   va_list args;

   va_start(args, fmt);
   vfprintf(stderr, fmt, args);
   fputc('\n', stderr);
   va_end(args);

   exit(EXIT_FAILURE);
}

/* FNV hash algorithm, version 1a, 32 bits. end is a pointer to the first
   character *not* to include in the hash, or NULL if all of str is to be
   included. */
unsigned int hash (char * str, char * end)
{
   unsigned int hash = 2166136261;
   unsigned char c;

   while ((str != end) && (c = *str++)) {
      hash ^= c;
      hash *= 16777619;
   }

   return hash;
}

/* Close the files in the given array, and free() the array. */
void output_close(FILE * out[], int ct)
{
   for (int i = 0; i < ct; i++)
      if (fclose(out[i]))
         fatal("error closing file: %s", errno);
   free(out);
}

/* Open the appropriate output files and return an array of file pointers. */
FILE ** output_open(char * basename, int ct)
{
   FILE ** out = calloc(ct, sizeof(FILE *));
   char * filename;

   for (int i = 0; i < ct; i++) {
      if (asprintf(&filename, "%s.%d", basename, i) == -1)
         fatal("asprintf() failed");
      out[i] = fopen(filename, "wb");
      if (!out[i])
         fatal("can't open %s: %s", filename, strerror(errno));
      setvbuf(out[i], NULL, _IOFBF, OUTPUT_BUFSIZE);
      free(filename);
   }

   return out;
}

/* Do the actual splitting of stdin. out is an array of open file descriptors,
   and output_ct is its length. */
void split(FILE ** out, int output_ct)
{
   char * line = NULL;
   size_t linebuf_sz = 0;
   ssize_t read_sz;
   char * end;

   while ((read_sz = getline(&line, &linebuf_sz, stdin)) != -1) {
      /* Set end to the first tab if one exists, else the trailing newline. If
         no newline is present, this will ignore the last byte of the key, but
         that is out of spec. */
      end = strchr(line, '\t');
      if (end == NULL)
         end = (line + read_sz - 1);
      fputs(line, out[hash(line, end) % output_ct]);
   }

   if (!feof(stdin))
      fatal("error reading intput: %s", strerror(errno));

   // if there is no input, line will still be NULL
   if (line)
      free(line);
}

/* Print a usage message and abort. */
void usage()
{
   fatal(
      /* If we were less lazy, we would use the executable name in argv[0]. */
      "usage: hashsplit N BASENAME\n"
      "\n"
      "Split standard input containing a stream of key/value lines separated\n"
      "by a single tab into N output files named BASENAME.i according to the\n"
      "hash values of the keys. The value may be absent, either with or\n"
      "without a tab following the key. Keys and values may contain any bytes\n"
      "except zero, tab, and newline.");
}
