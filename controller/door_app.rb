#!/usr/bin/env ruby

require 'yaml'
require 'socket'
require 'roda'
require 'tilt'

#
# Manages connection to a door system. This class should be instantiated for
# each door as it is accessed.
#
class DoorManager

  #
  # Initialize a connection to a door. The parameter is a hash having keys
  # 'name', 'host', and 'port'.
  #
  def initialize(door)
    @door = door
    @socket = TCPSocket.open(door['host'], door['port'])
  end

  #
  # Send a single-line query to the door system and receive a single-line
  # response.
  #
  def query(command, *args)
    cmd = [ command, *args ].join(" ")
    @socket.puts(cmd)
    return @socket.gets.chomp
  end

  #
  # Sends a query to the door system and receives a multi-line response, per the
  # door system protocol. According to that protocol, the first received line is
  # the number of following response lines.
  #
  def multiline_query(command, *args)
    lines = query(command, *args).chomp.to_i
    return (1..lines).map { |i| @socket.gets.chomp }
  end

  #
  # Close the underlying socket connection to the door system.
  #
  def close
    @socket.close
  end

  #
  # Analogous to IO.open, creates a new DoorManager object and executes the
  # given block with the created object. The DoorManager is closed upon
  # completion.
  #
  def self.open(door)
    dm = self.new(door)
    return dm unless block_given?
    begin
      return yield(dm)
    ensure
      dm.close
    end
  end
end

class DoorApp < Roda

  plugin :render, engine: :haml
  plugin :h

  route do |r|

    r.root do
      render "index", locals: { name: env['rack.session'][:name] }
    end

    r.on 'status' do
      res = {}
      opts[:config]['doors'].each do |door|
        begin
          res[door['name']] = DoorManager.open(door) { |dm| dm.query('status') }
        rescue
          res[door['name']] = "Error: #$!"
        end
      end
      render 'status', locals: { res: res }
    end

    r.on 'name', String do |str|
      env['rack.session'][:name] = str
      render 'name', locals: { name: str }
    end
  end
end
