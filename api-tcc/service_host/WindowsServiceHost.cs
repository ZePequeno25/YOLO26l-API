using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.ServiceProcess;
using System.Threading;

namespace ApiTcc.ServiceHost
{
    public sealed class WorkerService : ServiceBase
    {
        private readonly string configPath;
        private readonly ManualResetEvent stopEvent = new ManualResetEvent(false);
        private Thread workerThread;
        private Process childProcess;
        private bool stopping;

        public WorkerService(string serviceName, string configPath)
        {
            ServiceName = serviceName;
            this.configPath = configPath;
            CanStop = true;
            AutoLog = true;
        }

        protected override void OnStart(string[] args)
        {
            stopping = false;
            stopEvent.Reset();
            workerThread = new Thread(RunLoop);
            workerThread.IsBackground = true;
            workerThread.Start();
        }

        protected override void OnStop()
        {
            stopping = true;
            stopEvent.Set();
            StopChild();
            if (workerThread != null && workerThread.IsAlive)
            {
                workerThread.Join(TimeSpan.FromSeconds(30));
            }
        }

        private void RunLoop()
        {
            ServiceConfig config = ServiceConfig.Load(configPath);
            Directory.CreateDirectory(config.LogDirectory);

            while (!stopping)
            {
                try
                {
                    StartChild(config);
                    while (!stopping && childProcess != null && !childProcess.HasExited)
                    {
                        if (stopEvent.WaitOne(1000))
                        {
                            break;
                        }
                    }

                    if (stopping)
                    {
                        StopChild();
                        return;
                    }

                    File.AppendAllText(
                        Path.Combine(config.LogDirectory, ServiceName + ".host.log"),
                        DateTime.Now.ToString("s") + " child exited; restarting in 5 seconds." + Environment.NewLine
                    );
                    stopEvent.WaitOne(TimeSpan.FromSeconds(5));
                }
                catch (Exception ex)
                {
                    File.AppendAllText(
                        Path.Combine(config.LogDirectory, ServiceName + ".host.log"),
                        DateTime.Now.ToString("s") + " host error: " + ex + Environment.NewLine
                    );
                    stopEvent.WaitOne(TimeSpan.FromSeconds(5));
                }
            }
        }

        private void StartChild(ServiceConfig config)
        {
            string stdoutPath = Path.Combine(config.LogDirectory, ServiceName + ".out.log");
            string stderrPath = Path.Combine(config.LogDirectory, ServiceName + ".err.log");

            ProcessStartInfo startInfo = new ProcessStartInfo
            {
                FileName = config.Executable,
                Arguments = config.Arguments,
                WorkingDirectory = config.WorkingDirectory,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true
            };

            foreach (KeyValuePair<string, string> item in config.Environment)
            {
                startInfo.EnvironmentVariables[item.Key] = item.Value;
            }

            childProcess = new Process { StartInfo = startInfo, EnableRaisingEvents = true };
            childProcess.OutputDataReceived += delegate(object sender, DataReceivedEventArgs e)
            {
                if (e.Data != null) File.AppendAllText(stdoutPath, e.Data + Environment.NewLine);
            };
            childProcess.ErrorDataReceived += delegate(object sender, DataReceivedEventArgs e)
            {
                if (e.Data != null) File.AppendAllText(stderrPath, e.Data + Environment.NewLine);
            };
            childProcess.Start();
            childProcess.BeginOutputReadLine();
            childProcess.BeginErrorReadLine();
        }

        private void StopChild()
        {
            Process process = childProcess;
            if (process == null)
            {
                return;
            }

            try
            {
                if (!process.HasExited)
                {
                    process.Kill();
                    process.WaitForExit(10000);
                }
            }
            catch
            {
            }
            finally
            {
                try
                {
                    process.Dispose();
                }
                catch
                {
                }

                if (Object.ReferenceEquals(childProcess, process))
                {
                    childProcess = null;
                }
            }
        }
    }

    public sealed class ServiceConfig
    {
        public string Executable;
        public string Arguments;
        public string WorkingDirectory;
        public string LogDirectory;
        public Dictionary<string, string> Environment = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        public static ServiceConfig Load(string path)
        {
            ServiceConfig config = new ServiceConfig();
            foreach (string rawLine in File.ReadAllLines(path))
            {
                string line = rawLine.Trim();
                if (line.Length == 0 || line.StartsWith("#") || !line.Contains("="))
                {
                    continue;
                }

                string[] parts = line.Split(new[] { '=' }, 2);
                string key = parts[0].Trim();
                string value = parts[1].Trim();

                if (key.Equals("Executable", StringComparison.OrdinalIgnoreCase)) config.Executable = value;
                else if (key.Equals("Arguments", StringComparison.OrdinalIgnoreCase)) config.Arguments = value;
                else if (key.Equals("WorkingDirectory", StringComparison.OrdinalIgnoreCase)) config.WorkingDirectory = value;
                else if (key.Equals("LogDirectory", StringComparison.OrdinalIgnoreCase)) config.LogDirectory = value;
                else if (key.StartsWith("Env.", StringComparison.OrdinalIgnoreCase))
                {
                    config.Environment[key.Substring(4)] = value;
                }
            }

            if (String.IsNullOrWhiteSpace(config.Executable)) throw new InvalidOperationException("Executable ausente.");
            if (config.Arguments == null) config.Arguments = "";
            if (String.IsNullOrWhiteSpace(config.WorkingDirectory)) config.WorkingDirectory = Path.GetDirectoryName(path);
            if (String.IsNullOrWhiteSpace(config.LogDirectory)) config.LogDirectory = Path.Combine(config.WorkingDirectory, "logs");
            return config;
        }
    }

    internal static class Program
    {
        private static void Main(string[] args)
        {
            if (args.Length < 2)
            {
                throw new ArgumentException("Uso: WindowsServiceHost.exe <ServiceName> <ConfigPath>");
            }

            string configPath = String.Join(" ", args, 1, args.Length - 1);
            ServiceBase.Run(new WorkerService(args[0], configPath));
        }
    }
}
