using System;
using System.IO;
using System.IO.Compression;
using System.Text;

public static class UnzipShim
{
    public static int Main(string[] args)
    {
        Console.OutputEncoding = new UTF8Encoding(false);
        if (args.Length >= 2 && args[0] == "-Z1")
        {
            using (var archive = ZipFile.OpenRead(args[1]))
            {
                foreach (var entry in archive.Entries)
                    Console.Out.WriteLine(entry.FullName);
            }
            return 0;
        }

        if (args.Length >= 3 && args[0] == "-p")
        {
            using (var archive = ZipFile.OpenRead(args[1]))
            {
                foreach (var entry in archive.Entries)
                {
                    if (string.Equals(entry.FullName, args[2], StringComparison.Ordinal))
                    {
                        using (var input = entry.Open())
                        using (var output = Console.OpenStandardOutput())
                            input.CopyTo(output);
                        return 0;
                    }
                }
            }
            return 11;
        }

        return 2;
    }
}
